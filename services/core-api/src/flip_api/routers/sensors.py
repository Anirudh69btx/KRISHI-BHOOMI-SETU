"""
FLIP v3.0 — Core API REST Routers
Sensors router: ingest, query, and manual entry of sensor readings.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from flip_api.auth.keycloak import get_current_user, require_roles
from flip_api.database import get_session

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/sensors", tags=["sensors"])


# ─── Pydantic Models ──────────────────────────────────────────────────────────
from pydantic import BaseModel, Field


class ManualSensorEntry(BaseModel):
    farm_id: uuid.UUID
    sensor_id: str
    metric: str
    value: float
    unit: str
    recorded_at: Optional[datetime] = None


class SensorReadingResponse(BaseModel):
    sensor_id: str
    farm_id: str
    metric: str
    value: float
    unit: str
    quality: float
    recorded_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get(
    "/farms/{farm_id}",
    response_model=list[SensorReadingResponse],
    summary="Get latest sensor readings for a farm",
)
async def get_farm_sensors(
    farm_id: uuid.UUID,
    metric: Optional[str] = Query(None, description="Filter by metric type"),
    hours: int = Query(24, ge=1, le=168, description="Lookback window in hours"),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    since = datetime.now(tz=timezone.utc) - timedelta(hours=hours)

    # Use TimescaleDB time_bucket for efficiency
    query = text("""
        SELECT DISTINCT ON (sensor_id, metric)
            sensor_id,
            farm_id::text,
            metric,
            value,
            unit,
            quality,
            recorded_at,
            ST_Y(location::geometry) as latitude,
            ST_X(location::geometry) as longitude
        FROM sensor_readings
        WHERE farm_id = :farm_id
          AND recorded_at >= :since
          AND (:metric IS NULL OR metric = :metric)
        ORDER BY sensor_id, metric, recorded_at DESC
    """)

    result = await session.execute(
        query,
        {"farm_id": str(farm_id), "since": since, "metric": metric},
    )
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get(
    "/farms/{farm_id}/timeseries",
    summary="Get sensor time series (TimescaleDB bucketed)",
)
async def get_sensor_timeseries(
    farm_id: uuid.UUID,
    sensor_id: str,
    metric: str,
    bucket: str = Query("1 hour", description="TimescaleDB time_bucket interval"),
    hours: int = Query(48, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    since = datetime.now(tz=timezone.utc) - timedelta(hours=hours)

    query = text("""
        SELECT
            time_bucket(:bucket, recorded_at) AS bucket,
            AVG(value) AS avg_value,
            MIN(value) AS min_value,
            MAX(value) AS max_value,
            COUNT(*) AS sample_count
        FROM sensor_readings
        WHERE farm_id = :farm_id
          AND sensor_id = :sensor_id
          AND metric = :metric
          AND recorded_at >= :since
        GROUP BY bucket
        ORDER BY bucket ASC
    """)

    result = await session.execute(
        query,
        {
            "farm_id": str(farm_id),
            "sensor_id": sensor_id,
            "metric": metric,
            "bucket": bucket,
            "since": since,
        },
    )
    return [dict(r) for r in result.mappings().all()]


@router.post(
    "/manual",
    status_code=status.HTTP_201_CREATED,
    summary="Manual sensor data entry (offline sync)",
)
async def manual_sensor_entry(
    entry: ManualSensorEntry,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    recorded_at = entry.recorded_at or datetime.now(tz=timezone.utc)

    await session.execute(
        text("""
            INSERT INTO sensor_readings
                (farm_id, sensor_id, metric, value, unit, quality, recorded_at, ingested_by)
            VALUES
                (:farm_id, :sensor_id, :metric, :value, :unit, 1.0, :recorded_at, 'manual')
            ON CONFLICT DO NOTHING
        """),
        {
            "farm_id": str(entry.farm_id),
            "sensor_id": entry.sensor_id,
            "metric": entry.metric,
            "value": entry.value,
            "unit": entry.unit,
            "recorded_at": recorded_at,
        },
    )
    await session.commit()
    log.info(
        "manual_sensor_entry",
        farm_id=str(entry.farm_id),
        sensor_id=entry.sensor_id,
        metric=entry.metric,
        user=current_user.get("sub"),
    )
    return {"status": "created", "recorded_at": recorded_at.isoformat()}
