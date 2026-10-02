"""
FLIP Core API — Segment 05: Ingestion Service
=============================================
Exactly-once bulk ingestion pipeline.

POST /api/v1/telemetry/bulk
  • Pydantic schema validation + per-sensor range checks
  • Deduplication via (time, farm_id, device_id, sensor_type_id) PK
  • TimescaleDB bulk INSERT ... ON CONFLICT DO NOTHING (batches ≤ 1000)
  • Emit farm.{farm_id}.sensor.validated NATS event per batch
  • Prometheus metrics: ingestion_total, ingestion_latency_seconds,
                        ingestion_batch_size, ingestion_rejected_total
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from prometheus_client import REGISTRY, Counter, Histogram, Summary
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# ── Prometheus Metrics ────────────────────────────────────────────────────────

INGESTION_TOTAL = (
    REGISTRY._names_to_collectors.get("flip_ingestion_total")
    or Counter(
        "flip_ingestion_total",
        "Total sensor readings ingested",
        ["farm_id", "status"],
    )
)
INGESTION_LATENCY = (
    REGISTRY._names_to_collectors.get("flip_ingestion_latency_seconds")
    or Histogram(
        "flip_ingestion_latency_seconds",
        "End-to-end ingestion latency (NATS receive → DB commit)",
        ["farm_id"],
        buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    )
)
INGESTION_BATCH_SIZE = (
    REGISTRY._names_to_collectors.get("flip_ingestion_batch_size")
    or Histogram(
        "flip_ingestion_batch_size",
        "Number of readings per bulk-insert call",
        buckets=[1, 10, 50, 100, 250, 500, 1000],
    )
)
INGESTION_REJECTED = (
    REGISTRY._names_to_collectors.get("flip_ingestion_rejected_total")
    or Counter(
        "flip_ingestion_rejected_total",
        "Readings rejected due to validation failures",
        ["farm_id", "reason"],
    )
)
NATS_CONSUMER_LAG = (
    REGISTRY._names_to_collectors.get("flip_nats_consumer_lag_total")
    or Counter(
        "flip_nats_consumer_lag_total",
        "Messages consumed from NATS sensor stream",
        ["farm_id", "stream"],
    )
)

# ── Sensor range limits ───────────────────────────────────────────────────────

SENSOR_RANGES: dict[str, tuple[float, float]] = {
    "VWC":          (0.0, 100.0),
    "EC":           (0.0, 20.0),
    "TEMP_SOIL":    (-10.0, 80.0),
    "TEMP_AIR":     (-20.0, 60.0),
    "RH":           (0.0, 100.0),
    "LEAF_WETNESS": (0.0, 1.0),
    "RAIN":         (0.0, 300.0),
    "PAR":          (0.0, 3000.0),
    "WIND_S":       (0.0, 100.0),
    "WIND_D":       (0.0, 360.0),
    "BATTERY_MV":   (2000.0, 5000.0),
    "RSSI":         (-130.0, 0.0),
}

# ── Pydantic Models ───────────────────────────────────────────────────────────

class SensorReadingIn(BaseModel):
    """Single sensor reading payload (from NATS / gateway)."""

    farm_id:        uuid.UUID
    field_id:       Optional[uuid.UUID] = None
    device_id:      uuid.UUID
    sensor_type_id: uuid.UUID
    time:           datetime
    value:          float
    quality_flag:   str = "RAW"
    sensor_code:    Optional[str] = None   # e.g. "VWC", populated from join
    metadata:       dict[str, Any] = Field(default_factory=dict)

    # EKF-augmented fields (optional — set by gateway)
    corrected_value:  Optional[float] = None
    residual:         Optional[float] = None
    is_anomaly:       bool = False
    ekf_covariance:   Optional[float] = None

    @field_validator("time", mode="before")
    @classmethod
    def parse_time(cls, v: Any) -> datetime:
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v

    @field_validator("quality_flag")
    @classmethod
    def valid_flag(cls, v: str) -> str:
        allowed = {"RAW", "EKF_CORRECTED", "ANOMALY", "BUFFERED", "VALIDATED"}
        if v not in allowed:
            raise ValueError(f"quality_flag must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def ensure_utc(self) -> "SensorReadingIn":
        if self.time.tzinfo is None:
            self.time = self.time.replace(tzinfo=timezone.utc)
        return self


class BulkIngestionRequest(BaseModel):
    """Bulk telemetry ingestion request."""

    readings: list[SensorReadingIn] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="1–1000 sensor readings per call",
    )
    batch_id: Optional[str] = None  # caller-assigned idempotency key


class IngestionResult(BaseModel):
    inserted:  int
    skipped:   int   # duplicates
    rejected:  int
    batch_id:  Optional[str] = None
    latency_ms: float


# ── Range Validation ──────────────────────────────────────────────────────────

def validate_range(reading: SensorReadingIn) -> tuple[bool, str]:
    """Return (valid, reason). Uses sensor_code if available."""
    code = (reading.sensor_code or "").upper()
    if code not in SENSOR_RANGES:
        return True, ""  # unknown sensor — pass through
    lo, hi = SENSOR_RANGES[code]
    if not (lo <= reading.value <= hi):
        return False, f"out_of_range:{code}:{reading.value:.2f}"
    return True, ""


# ── Ingestion Service ─────────────────────────────────────────────────────────

class IngestionService:
    """
    Core ingestion pipeline service.
    Wired to FastAPI via dependency injection — receives an open AsyncSession
    and a reference to the NATSClient.
    """

    MAX_BATCH = 1000

    def __init__(self, session: AsyncSession, nats_client: Any):
        self.session = session
        self.nats = nats_client

    async def ingest_bulk(
        self, request: BulkIngestionRequest
    ) -> IngestionResult:
        """
        Main entry-point. Called from the router for POST /telemetry/bulk.
        1. Validate ranges
        2. Bulk-insert (dedup via ON CONFLICT DO NOTHING)
        3. Emit NATS validated events per farm
        4. Record Prometheus metrics
        """
        t0 = time.perf_counter()
        readings = request.readings
        batch_id = request.batch_id or str(uuid.uuid4())

        INGESTION_BATCH_SIZE.observe(len(readings))

        # Group readings by farm for NATS publishing
        farm_batches: dict[str, list[SensorReadingIn]] = {}
        valid_rows: list[dict[str, Any]] = []
        rejected = 0

        for r in readings:
            ok, reason = validate_range(r)
            if not ok:
                farm_id_str = str(r.farm_id)
                INGESTION_REJECTED.labels(farm_id=farm_id_str, reason=reason).inc()
                INGESTION_TOTAL.labels(farm_id=farm_id_str, status="rejected").inc()
                rejected += 1
                continue

            farm_id_str = str(r.farm_id)
            farm_batches.setdefault(farm_id_str, []).append(r)
            valid_rows.append(self._to_db_row(r))

        # Bulk insert — ON CONFLICT DO NOTHING for exactly-once
        inserted = 0
        if valid_rows:
            inserted = await self._bulk_insert(valid_rows)

        skipped = len(valid_rows) - inserted

        # Emit NATS validated events (fan-out per farm)
        if self.nats is not None:
            for farm_id_str, farm_readings in farm_batches.items():
                try:
                    payload = {
                        "batch_id": batch_id,
                        "farm_id": farm_id_str,
                        "count": len(farm_readings),
                        "readings": [r.model_dump(mode="json") for r in farm_readings],
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await self.nats.publish(
                        f"farm.{farm_id_str}.sensor.validated", payload
                    )
                    NATS_CONSUMER_LAG.labels(
                        farm_id=farm_id_str, stream="FARM_SENSOR"
                    ).inc(len(farm_readings))
                except Exception as exc:
                    logger.warning(
                        "nats_publish_failed",
                        farm_id=farm_id_str,
                        error=str(exc),
                    )

        # Prometheus
        latency_ms = (time.perf_counter() - t0) * 1000
        for farm_id_str in farm_batches:
            INGESTION_TOTAL.labels(farm_id=farm_id_str, status="accepted").inc(
                len(farm_batches[farm_id_str])
            )
            INGESTION_LATENCY.labels(farm_id=farm_id_str).observe(latency_ms / 1000)

        logger.info(
            "ingestion_bulk_complete",
            batch_id=batch_id,
            inserted=inserted,
            skipped=skipped,
            rejected=rejected,
            latency_ms=round(latency_ms, 2),
        )

        return IngestionResult(
            inserted=inserted,
            skipped=skipped,
            rejected=rejected,
            batch_id=batch_id,
            latency_ms=round(latency_ms, 2),
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _to_db_row(r: SensorReadingIn) -> dict[str, Any]:
        """Convert Pydantic model to raw dict for SQLAlchemy bulk insert."""
        import json
        return {
            "time":           r.time,
            "farm_id":        str(r.farm_id),
            "field_id":       str(r.field_id) if r.field_id else None,
            "device_id":      str(r.device_id),
            "sensor_type_id": str(r.sensor_type_id),
            "value":          r.corrected_value if r.corrected_value is not None else r.value,
            "quality_flag":   "ANOMALY" if r.is_anomaly else ("EKF_CORRECTED" if r.corrected_value is not None else r.quality_flag),
            "metadata":       json.dumps({
                **r.metadata,
                **({"residual": r.residual} if r.residual is not None else {}),
                **({"ekf_covariance": r.ekf_covariance} if r.ekf_covariance is not None else {}),
            }),
        }

    async def _bulk_insert(self, rows: list[dict[str, Any]]) -> int:
        """
        Bulk-insert up to MAX_BATCH rows per statement.
        ON CONFLICT DO NOTHING implements exactly-once deduplication.
        Returns total rows actually inserted.
        """
        stmt = text("""
            INSERT INTO sensor_readings
                (time, farm_id, field_id, device_id, sensor_type_id,
                 value, quality_flag, metadata)
            VALUES
                (:time, :farm_id, :field_id, :device_id, :sensor_type_id,
                 :value, :quality_flag, :metadata::jsonb)
            ON CONFLICT (time, farm_id, device_id, sensor_type_id)
            DO NOTHING
        """)
        total_inserted = 0
        for i in range(0, len(rows), self.MAX_BATCH):
            chunk = rows[i : i + self.MAX_BATCH]
            result = await self.session.execute(stmt, chunk)
            total_inserted += result.rowcount
        return total_inserted


# ── FastAPI Router (plugged into main.py) ─────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

telemetry_router = APIRouter(prefix="/telemetry", tags=["Telemetry Ingestion"])


async def get_nats_client() -> Any:
    """Dependency: import nats_client from main module at request time."""
    from flip_api.main import nats_client  # type: ignore[attr-defined]
    return nats_client


async def get_db_session() -> AsyncSession:
    """Dependency: yield a database session."""
    from flip_api.database import get_session  # type: ignore[attr-defined]
    async with get_session() as session:
        yield session


@telemetry_router.post(
    "/bulk",
    response_model=IngestionResult,
    status_code=status.HTTP_200_OK,
    summary="Bulk telemetry ingestion (exactly-once)",
    description=(
        "Accept 1-1000 sensor readings. Validates ranges, deduplicates via "
        "TimescaleDB PK, emits NATS validated events, records Prometheus metrics."
    ),
)
async def bulk_ingest(
    request: BulkIngestionRequest,
    session: AsyncSession = Depends(get_db_session),
    nats_client: Any = Depends(get_nats_client),
) -> IngestionResult:
    svc = IngestionService(session=session, nats_client=nats_client)
    try:
        result = await svc.ingest_bulk(request)
    except Exception as exc:
        logger.error("ingestion_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {exc}",
        )
    return result
