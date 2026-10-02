"""
FLIP Core API — Segment 05: Sensor Health Scoring Service
=========================================================
Computes composite 0-100 health score per device-sensor pair.
Schedule: daily 03:00 UTC + on-demand after anomaly detection.

Scoring factors (weighted sum = 100):
  30%  Anomaly Frequency      — 100 - min(100, anomaly_count_30d * 5)
  20%  Battery Trend          — linear regression slope over 30d
  20%  Signal Quality (RSSI)  — map [-120, -60] dBm → [0, 100]
  15%  Calibration Age        — max(0, 100 - days_since_calibration * 2)
  15%  Data Completeness      — (actual / expected readings over 30d) * 100

Actions:
  • Update device_sensors.health_score + health_factors + last_health_check
  • If score < 60 → insert maintenance_tickets + emit NATS health.degraded
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import numpy as np
import structlog
from prometheus_client import Counter, Gauge
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# ── Prometheus ────────────────────────────────────────────────────────────────

HEALTH_SCORE_GAUGE = Gauge(
    "flip_sensor_health_score",
    "Current sensor health score (0-100)",
    ["farm_id", "device_id", "sensor_type"],
)
TICKETS_TOTAL = Counter(
    "flip_maintenance_tickets_total",
    "Maintenance tickets created",
    ["farm_id", "priority"],
)

# ── Scoring constants ─────────────────────────────────────────────────────────

WEIGHT_ANOMALY       = 0.30
WEIGHT_BATTERY       = 0.20
WEIGHT_RSSI          = 0.20
WEIGHT_CALIBRATION   = 0.15
WEIGHT_COMPLETENESS  = 0.15

HEALTH_DEGRADED_THRESHOLD  = 60
READINGS_PER_DAY_EXPECTED  = 96   # every 15 min × 4 × 24
DAYS_WINDOW                = 30


# ── Factor calculators ────────────────────────────────────────────────────────

def score_anomaly_frequency(anomaly_count_30d: int) -> float:
    """30%: 100 - min(100, anomaly_count * 5)."""
    return max(0.0, 100.0 - min(100.0, float(anomaly_count_30d) * 5.0))


def score_battery_trend(battery_readings: list[float]) -> float:
    """
    20%: Linear regression slope of battery_mv over 30 days.
    > 0 mV/day → 100
    < -5 mV/day → 0
    Interpolated in between.
    """
    if len(battery_readings) < 2:
        return 70.0  # neutral if insufficient data
    x = np.arange(len(battery_readings), dtype=float)
    y = np.array(battery_readings, dtype=float)
    if np.std(x) == 0:
        return 70.0
    slope = float(np.polyfit(x, y, 1)[0])
    # scale: 0 → 100, -5 → 0, linear
    clamped = max(-5.0, min(0.0, slope))
    return round(100.0 + clamped * 20.0, 2)   # 0 → 100, -5 → 0


def score_rssi(avg_rssi_dbm: Optional[float]) -> float:
    """
    20%: Map [-120, -60] dBm → [0, 100].
    (rssi + 120) * 2  clamped [0, 100].
    """
    if avg_rssi_dbm is None:
        return 50.0  # neutral
    return round(float(np.clip((avg_rssi_dbm + 120.0) * 2.0, 0.0, 100.0)), 2)


def score_calibration_age(days_since_calibration: Optional[float]) -> float:
    """
    15%: max(0, 100 - days_since_calibration * 2).
    Recalibrate yearly → 0 score at 50 days past due.
    """
    if days_since_calibration is None:
        return 80.0  # assume recently calibrated
    return max(0.0, round(100.0 - float(days_since_calibration) * 2.0, 2))


def score_data_completeness(actual: int, expected: int) -> float:
    """15%: (actual / expected) * 100, clamped [0, 100]."""
    if expected == 0:
        return 0.0
    return round(float(np.clip((actual / expected) * 100.0, 0.0, 100.0)), 2)


def compute_composite_score(factors: dict[str, float]) -> int:
    """Compute weighted sum and round to integer."""
    score = (
        factors["anomaly_frequency"] * WEIGHT_ANOMALY
        + factors["battery_trend"] * WEIGHT_BATTERY
        + factors["rssi"] * WEIGHT_RSSI
        + factors["calibration_age"] * WEIGHT_CALIBRATION
        + factors["data_completeness"] * WEIGHT_COMPLETENESS
    )
    return int(round(max(0.0, min(100.0, score))))


# ── DB queries ────────────────────────────────────────────────────────────────

async def _fetch_devices_for_farm(
    session: AsyncSession, farm_id: str
) -> list[dict[str, Any]]:
    """Return list of {device_id, sensor_type_id, sensor_code, calibrated_at} dicts."""
    result = await session.execute(
        text("""
            SELECT
                ds.id         AS device_sensor_id,
                ds.device_id,
                ds.sensor_type_id,
                st.code       AS sensor_code,
                ds.health_score AS current_score,
                ds.last_health_check
            FROM device_sensors ds
            JOIN sensor_types   st ON ds.sensor_type_id = st.id
            JOIN devices         d ON ds.device_id = d.id
            WHERE d.farm_id = :fid
              AND ds.active  = TRUE
        """),
        {"fid": farm_id},
    )
    return [dict(r._mapping) for r in result.fetchall()]


async def _fetch_anomaly_count(
    session: AsyncSession, device_id: str, sensor_type_id: str
) -> int:
    r = await session.execute(
        text("""
            SELECT count(*) AS cnt
            FROM sensor_anomalies
            WHERE device_id      = :did
              AND sensor_type_id = :stid
              AND detected_at    > now() - INTERVAL '30 days'
        """),
        {"did": device_id, "stid": sensor_type_id},
    )
    return int(r.scalar() or 0)


async def _fetch_battery_trend(
    session: AsyncSession, device_id: str
) -> list[float]:
    """Fetch daily average battery_mv from metadata JSONB over 30d."""
    r = await session.execute(
        text("""
            SELECT avg((metadata->>'battery_mv')::float) AS avg_mv
            FROM sensor_readings
            WHERE device_id = :did
              AND time > now() - INTERVAL '30 days'
              AND metadata ? 'battery_mv'
            GROUP BY time_bucket('1 day', time)
            ORDER BY 1
        """),
        {"did": device_id},
    )
    return [float(row.avg_mv) for row in r.fetchall() if row.avg_mv is not None]


async def _fetch_avg_rssi(
    session: AsyncSession, device_id: str
) -> Optional[float]:
    r = await session.execute(
        text("""
            SELECT avg((metadata->>'rssi')::float) AS avg_rssi
            FROM sensor_readings
            WHERE device_id = :did
              AND time > now() - INTERVAL '30 days'
              AND metadata ? 'rssi'
        """),
        {"did": device_id},
    )
    val = r.scalar()
    return float(val) if val is not None else None


async def _fetch_reading_count(
    session: AsyncSession, device_id: str, sensor_type_id: str
) -> int:
    r = await session.execute(
        text("""
            SELECT count(*) AS cnt
            FROM sensor_readings
            WHERE device_id      = :did
              AND sensor_type_id = :stid
              AND time > now() - INTERVAL '30 days'
        """),
        {"did": device_id, "stid": sensor_type_id},
    )
    return int(r.scalar() or 0)


# ── Maintenance ticket creation ───────────────────────────────────────────────

async def _create_ticket(
    session: AsyncSession,
    farm_id: str,
    device_id: str,
    sensor_type_id: str,
    score: int,
    factors: dict[str, float],
) -> str:
    """Insert a maintenance ticket based on which factor degraded most."""
    # Determine ticket type from worst factor
    worst_factor = min(factors, key=lambda k: factors[k])
    ticket_type_map = {
        "battery_trend":    "BATTERY_REPLACE",
        "anomaly_frequency":"HARDWARE_REPAIR",
        "rssi":             "REPOSITION",
        "calibration_age":  "CALIBRATION",
        "data_completeness":"HARDWARE_REPAIR",
    }
    ticket_type = ticket_type_map.get(worst_factor, "HARDWARE_REPAIR")
    priority = "URGENT" if score < 40 else "HIGH" if score < 50 else "MEDIUM"

    description = (
        f"Sensor health score dropped to {score}/100. "
        f"Degraded factors: {json.dumps({k: round(v,1) for k, v in factors.items()})}. "
        f"Primary issue: {worst_factor.replace('_', ' ')} = {round(factors[worst_factor], 1)}/100."
    )

    result = await session.execute(
        text("""
            INSERT INTO maintenance_tickets
                (farm_id, device_id, sensor_type_id, ticket_type, priority,
                 description, status, health_score_at_creation)
            VALUES
                (:farm_id, :device_id, :sensor_type_id, :ticket_type, :priority,
                 :description, 'OPEN', :health_score)
            RETURNING id
        """),
        {
            "farm_id":        farm_id,
            "device_id":      device_id,
            "sensor_type_id": sensor_type_id,
            "ticket_type":    ticket_type,
            "priority":       priority,
            "description":    description,
            "health_score":   score,
        },
    )
    ticket_id = str(result.scalar())
    TICKETS_TOTAL.labels(farm_id=farm_id, priority=priority).inc()
    return ticket_id


# ── Main service ──────────────────────────────────────────────────────────────

class HealthScoringService:
    """
    Computes and persists sensor health scores for all devices on a farm.
    """

    def __init__(self, session: AsyncSession, nats_client: Any):
        self.session = session
        self.nats = nats_client

    async def run_farm(self, farm_id: str) -> list[dict[str, Any]]:
        """
        Compute health scores for all device-sensors on a farm.
        Returns list of result dicts.
        """
        devices = await _fetch_devices_for_farm(self.session, farm_id)
        if not devices:
            logger.info("health_scoring_no_devices", farm_id=farm_id)
            return []

        results = []
        for dev in devices:
            result = await self._score_device_sensor(farm_id, dev)
            results.append(result)

        logger.info(
            "health_scoring_farm_done",
            farm_id=farm_id,
            devices=len(results),
        )
        return results

    async def _score_device_sensor(
        self, farm_id: str, dev: dict[str, Any]
    ) -> dict[str, Any]:
        device_id      = str(dev["device_id"])
        sensor_type_id = str(dev["sensor_type_id"])
        sensor_code    = dev["sensor_code"]
        prev_score     = dev.get("current_score", 100)

        # 1. Gather all factor inputs in parallel (asyncio.gather for speed)
        import asyncio
        (
            anomaly_count,
            battery_readings,
            avg_rssi,
            reading_count,
        ) = await asyncio.gather(
            _fetch_anomaly_count(self.session, device_id, sensor_type_id),
            _fetch_battery_trend(self.session, device_id),
            _fetch_avg_rssi(self.session, device_id),
            _fetch_reading_count(self.session, device_id, sensor_type_id),
        )

        expected_count = READINGS_PER_DAY_EXPECTED * DAYS_WINDOW

        # 2. Compute individual factor scores
        factors = {
            "anomaly_frequency": score_anomaly_frequency(anomaly_count),
            "battery_trend":     score_battery_trend(battery_readings),
            "rssi":              score_rssi(avg_rssi),
            "calibration_age":   score_calibration_age(None),  # TODO: pull from device_sensors
            "data_completeness": score_data_completeness(reading_count, expected_count),
        }

        # 3. Composite score
        health_score = compute_composite_score(factors)

        # 4. Persist to device_sensors
        await self.session.execute(
            text("""
                UPDATE device_sensors
                SET health_score      = :score,
                    last_health_check = now(),
                    health_factors    = :factors::jsonb
                WHERE device_id      = :device_id
                  AND sensor_type_id = :sensor_type_id
            """),
            {
                "score":          health_score,
                "factors":        json.dumps(factors),
                "device_id":      device_id,
                "sensor_type_id": sensor_type_id,
            },
        )

        # 5. Prometheus gauge
        HEALTH_SCORE_GAUGE.labels(
            farm_id=farm_id,
            device_id=device_id,
            sensor_type=sensor_code,
        ).set(health_score)

        result = {
            "device_id":      device_id,
            "sensor_type_id": sensor_type_id,
            "sensor_code":    sensor_code,
            "health_score":   health_score,
            "factors":        factors,
        }

        # 6. Trigger maintenance ticket if score < threshold and was above
        if health_score < HEALTH_DEGRADED_THRESHOLD and (
            prev_score is None or prev_score >= HEALTH_DEGRADED_THRESHOLD
        ):
            ticket_id = await _create_ticket(
                self.session, farm_id, device_id, sensor_type_id,
                health_score, factors
            )
            result["ticket_id"] = ticket_id

            # Emit NATS health.degraded
            await self._emit_health_degraded(farm_id, device_id, health_score, factors)

        return result

    async def _emit_health_degraded(
        self,
        farm_id: str,
        device_id: str,
        health_score: int,
        factors: dict[str, float],
    ) -> None:
        if self.nats is None:
            return
        try:
            await self.nats.publish(
                f"farm.{farm_id}.sensor.health.degraded",
                {
                    "farm_id":     farm_id,
                    "device_id":   device_id,
                    "health_score": health_score,
                    "factors":     factors,
                    "timestamp":   datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as exc:
            logger.warning("nats_health_publish_failed", error=str(exc))
