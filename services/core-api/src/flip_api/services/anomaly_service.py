"""
FLIP Core API — Segment 05: Cloud Isolation Forest Anomaly Service
==================================================================
Batch multivariate anomaly detection via sklearn IsolationForest.
Schedule: every 15 minutes (Temporal.io or Celery Beat).

Flow:
  1. Pull last 4h sensor readings per farm (7 features, 15-min buckets)
  2. Load per-farm model from MinIO (or train fresh if absent)
  3. Score samples → emit anomaly events to NATS + persist to DB
  4. Daily retrain at 02:00 UTC on last 30 days of data
"""
from __future__ import annotations

import io
import json
import logging
import math
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import numpy as np
import structlog
from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# ── Prometheus ────────────────────────────────────────────────────────────────

ANOMALY_TOTAL = Counter(
    "flip_anomaly_total",
    "Anomalies detected",
    ["farm_id", "type", "severity"],
)
IF_TRAINING_DURATION = Histogram(
    "flip_isolation_forest_training_duration_seconds",
    "IF model training duration",
    ["farm_id"],
    buckets=[1, 5, 15, 30, 60, 120, 300],
)
IF_MODEL_AGE = Gauge(
    "flip_isolation_forest_model_age_hours",
    "Hours since last IF model training",
    ["farm_id"],
)
ANOMALY_DETECTION_LATENCY = Histogram(
    "flip_anomaly_detection_latency_seconds",
    "IF inference latency",
    ["farm_id"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

# ── Feature config ────────────────────────────────────────────────────────────

FEATURE_SENSORS = ["VWC", "EC", "TEMP_SOIL", "TEMP_AIR", "RH", "LEAF_WETNESS", "PAR"]
IF_CONTAMINATION = 0.01
IF_N_ESTIMATORS  = 200
IF_MAX_SAMPLES   = 256
IF_RANDOM_STATE  = 42
MIN_SAMPLES_FOR_INFERENCE = 100
WINDOW_HOURS_INFERENCE    = 4
WINDOW_DAYS_TRAINING      = 30


# ── Data fetching ─────────────────────────────────────────────────────────────

async def fetch_multivariate_window(
    session: AsyncSession,
    farm_id: str,
    hours: int = WINDOW_HOURS_INFERENCE,
) -> Optional[np.ndarray]:
    """
    Fetch last `hours` of sensor data for a farm, resampled to 15-min buckets.
    Returns (N, 7) ndarray or None if insufficient data.
    """
    query = text("""
        SELECT
            time_bucket('15 minutes', sr.time) AS bucket,
            st.code,
            avg(sr.value)                       AS avg_val
        FROM sensor_readings sr
        JOIN sensor_types    st ON sr.sensor_type_id = st.id
        WHERE sr.farm_id  = :fid
          AND sr.time     > now() - make_interval(hours => :hrs)
          AND st.code     = ANY(:codes)
          AND sr.quality_flag IN ('RAW', 'EKF_CORRECTED')
        GROUP BY bucket, st.code
        ORDER BY bucket ASC
    """)
    result = await session.execute(
        query,
        {"fid": farm_id, "hrs": hours, "codes": FEATURE_SENSORS},
    )
    rows = result.fetchall()
    if not rows:
        return None

    # Pivot: bucket → {code: value}
    from collections import defaultdict
    pivot: dict[datetime, dict[str, float]] = defaultdict(dict)
    for row in rows:
        pivot[row.bucket][row.code] = float(row.avg_val)

    # Build matrix in time order; forward-fill missing values
    times = sorted(pivot.keys())
    matrix = []
    last_row: dict[str, float] = {c: 0.0 for c in FEATURE_SENSORS}
    for t in times:
        for code in FEATURE_SENSORS:
            if code in pivot[t]:
                last_row[code] = pivot[t][code]
        matrix.append([last_row[c] for c in FEATURE_SENSORS])

    arr = np.array(matrix, dtype=np.float32)
    if len(arr) < MIN_SAMPLES_FOR_INFERENCE:
        logger.info(
            "if_insufficient_samples",
            farm_id=farm_id,
            samples=len(arr),
            required=MIN_SAMPLES_FOR_INFERENCE,
        )
        return None
    return arr


async def fetch_training_window(
    session: AsyncSession,
    farm_id: str,
    days: int = WINDOW_DAYS_TRAINING,
) -> Optional[np.ndarray]:
    """Fetch 30-day training window (same query, larger window)."""
    return await fetch_multivariate_window(session, farm_id, hours=days * 24)


# ── Model persistence (MinIO via S3) ─────────────────────────────────────────

class ModelStore:
    """
    Persist/load IsolationForest models via MinIO (S3-compatible).
    Falls back gracefully if MinIO is unavailable.
    """
    BUCKET = "ml-models"

    def __init__(self) -> None:
        self._client: Any = None
        try:
            import boto3  # type: ignore
            self._client = boto3.client(
                "s3",
                endpoint_url=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
                aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            )
        except Exception as exc:
            logger.warning("minio_unavailable", error=str(exc))

    def _key(self, farm_id: str) -> str:
        return f"anomaly/{farm_id}/isolation_forest_latest.joblib"

    def save(self, farm_id: str, model: Any, timestamp: str) -> bool:
        """Serialize and upload model to MinIO."""
        if self._client is None:
            return False
        try:
            import joblib  # type: ignore
            buf = io.BytesIO()
            joblib.dump({"model": model, "trained_at": timestamp, "features": FEATURE_SENSORS}, buf)
            buf.seek(0)
            self._client.put_object(
                Bucket=self.BUCKET,
                Key=self._key(farm_id),
                Body=buf,
                ContentType="application/octet-stream",
            )
            logger.info("if_model_saved", farm_id=farm_id)
            return True
        except Exception as exc:
            logger.warning("if_model_save_failed", farm_id=farm_id, error=str(exc))
            return False

    def load(self, farm_id: str) -> Optional[Any]:
        """Download and deserialize model from MinIO."""
        if self._client is None:
            return None
        try:
            import joblib  # type: ignore
            response = self._client.get_object(Bucket=self.BUCKET, Key=self._key(farm_id))
            buf = io.BytesIO(response["Body"].read())
            data = joblib.load(buf)
            return data.get("model")
        except Exception:
            return None


# ── Isolation Forest Service ──────────────────────────────────────────────────

class AnomalyService:
    """
    Cloud batch anomaly detection service using sklearn IsolationForest.
    One model per farm, trained on the farm's own historical data.
    """

    def __init__(self, session: AsyncSession, nats_client: Any):
        self.session = session
        self.nats = nats_client
        self._models: dict[str, Any] = {}        # in-memory model cache
        self._store = ModelStore()

    # ── Training ──────────────────────────────────────────────────────────────

    async def train(self, farm_id: str) -> bool:
        """
        Train IsolationForest on 30 days of farm data.
        Called daily at 02:00 UTC.
        """
        import time as _time
        t0 = _time.perf_counter()

        X = await fetch_training_window(self.session, farm_id)
        if X is None:
            logger.warning("if_train_no_data", farm_id=farm_id)
            return False

        from sklearn.ensemble import IsolationForest  # type: ignore
        model = IsolationForest(
            contamination=IF_CONTAMINATION,
            n_estimators=IF_N_ESTIMATORS,
            max_samples=IF_MAX_SAMPLES,
            random_state=IF_RANDOM_STATE,
            n_jobs=-1,
        )
        model.fit(X)

        duration = _time.perf_counter() - t0
        IF_TRAINING_DURATION.labels(farm_id=farm_id).observe(duration)

        ts = datetime.now(timezone.utc).isoformat()
        self._models[farm_id] = model
        self._store.save(farm_id, model, ts)

        logger.info(
            "if_train_complete",
            farm_id=farm_id,
            samples=len(X),
            duration_s=round(duration, 2),
        )
        return True

    def _load_model(self, farm_id: str) -> Optional[Any]:
        """Return cached model or load from MinIO."""
        if farm_id in self._models:
            return self._models[farm_id]
        model = self._store.load(farm_id)
        if model is not None:
            self._models[farm_id] = model
        return model

    # ── Inference ─────────────────────────────────────────────────────────────

    async def run_inference(self, farm_id: str) -> list[dict]:
        """
        Score last 4h of data.
        Returns list of anomaly event dicts.
        """
        import time as _time
        t0 = _time.perf_counter()

        model = self._load_model(farm_id)
        if model is None:
            logger.info("if_no_model_training", farm_id=farm_id)
            await self.train(farm_id)
            model = self._load_model(farm_id)
            if model is None:
                return []

        X = await fetch_multivariate_window(self.session, farm_id)
        if X is None:
            return []

        scores = model.score_samples(X)          # negative = more anomalous
        labels = model.predict(X)                # -1 = anomaly

        latency = _time.perf_counter() - t0
        ANOMALY_DETECTION_LATENCY.labels(farm_id=farm_id).observe(latency)

        anomalies = []
        for i, (score, label) in enumerate(zip(scores, labels)):
            if label == -1:
                sensor_vals = dict(zip(FEATURE_SENSORS, X[i].tolist()))
                severity = "CRITICAL" if score < -0.3 else "WARNING"
                anomaly = {
                    "id":             str(uuid.uuid4()),
                    "farm_id":        farm_id,
                    "detected_at":    datetime.now(timezone.utc).isoformat(),
                    "anomaly_type":   "ISOLATION_FOREST",
                    "severity":       severity,
                    "anomaly_score":  round(float(score), 6),
                    "sensor_values":  sensor_vals,
                    "type":           "MULTIVARIATE_DRIFT",
                }
                anomalies.append(anomaly)
                ANOMALY_TOTAL.labels(
                    farm_id=farm_id, type="ISOLATION_FOREST", severity=severity
                ).inc()

        logger.info(
            "if_inference_complete",
            farm_id=farm_id,
            total=len(X),
            anomalies=len(anomalies),
            latency_ms=round(latency * 1000, 2),
        )
        return anomalies

    # ── Persistence ───────────────────────────────────────────────────────────

    async def persist_anomaly(self, anomaly: dict) -> None:
        """Insert anomaly event into sensor_anomalies hypertable."""
        stmt = text("""
            INSERT INTO sensor_anomalies
                (farm_id, detected_at, anomaly_type, severity,
                 anomaly_score, sensor_snapshot)
            VALUES
                (:farm_id, :detected_at, :anomaly_type, :severity,
                 :anomaly_score, :sensor_snapshot::jsonb)
            ON CONFLICT DO NOTHING
        """)
        await self.session.execute(stmt, {
            "farm_id":        anomaly["farm_id"],
            "detected_at":    anomaly["detected_at"],
            "anomaly_type":   anomaly["anomaly_type"],
            "severity":       anomaly["severity"],
            "anomaly_score":  anomaly["anomaly_score"],
            "sensor_snapshot": json.dumps(anomaly.get("sensor_values", {})),
        })

    async def persist_ekf_anomaly(
        self,
        farm_id: str,
        device_id: str,
        sensor_type_id: str,
        raw_value: float,
        corrected_value: float,
        residual: float,
        ekf_covariance: float,
        severity: str = "WARNING",
    ) -> None:
        """Insert EKF point anomaly event."""
        stmt = text("""
            INSERT INTO sensor_anomalies
                (farm_id, device_id, sensor_type_id, detected_at,
                 anomaly_type, severity, raw_value, expected_value,
                 residual, ekf_covariance)
            VALUES
                (:farm_id, :device_id, :sensor_type_id, now(),
                 'EKF_POINT', :severity, :raw_value, :expected_value,
                 :residual, :ekf_covariance)
        """)
        await self.session.execute(stmt, {
            "farm_id":        farm_id,
            "device_id":      device_id,
            "sensor_type_id": sensor_type_id,
            "severity":       severity,
            "raw_value":      raw_value,
            "expected_value": corrected_value,
            "residual":       residual,
            "ekf_covariance": ekf_covariance,
        })
        ANOMALY_TOTAL.labels(farm_id=farm_id, type="EKF_POINT", severity=severity).inc()

    # ── NATS emit ─────────────────────────────────────────────────────────────

    async def emit_anomaly_event(self, anomaly: dict) -> None:
        """Publish anomaly to NATS farm.{id}.sensor.anomaly."""
        if self.nats is None:
            return
        farm_id = anomaly["farm_id"]
        try:
            await self.nats.publish(f"farm.{farm_id}.sensor.anomaly", anomaly)
        except Exception as exc:
            logger.warning("nats_anomaly_publish_failed", error=str(exc))
