"""
FLIP Core API — SensorRepository
TimescaleDB-optimised sensor reading access.
All queries use parameter binding — no string interpolation except for
sensor_codes which are validated against an allowlist before use.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from .base import BaseRepository

logger = structlog.get_logger(__name__)

# Allowlist for sensor code values (prevents SQL injection in time_bucket query)
_SAFE_CODE_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)
_SAFE_INTERVALS = frozenset(
    {"1 minute", "5 minutes", "15 minutes", "1 hour", "6 hours", "1 day"}
)


def _validate_codes(codes: list[str]) -> list[str]:
    for code in codes:
        if not all(c in _SAFE_CODE_CHARS for c in code):
            raise ValueError(f"Unsafe sensor code: {code!r}")
    return codes


def _validate_interval(interval: str) -> str:
    if interval not in _SAFE_INTERVALS:
        raise ValueError(
            f"Invalid interval {interval!r}. Allowed: {_SAFE_INTERVALS}"
        )
    return interval


class SensorRepository(BaseRepository):
    """TimescaleDB-backed sensor reading repository."""

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def bulk_insert(self, readings: list[dict[str, Any]]) -> int:
        """
        Bulk insert sensor readings using ON CONFLICT DO NOTHING.
        Readings must be plain dicts matching the sensor_readings schema.
        Returns number of rows actually inserted.
        """
        if not readings:
            return 0

        stmt = text("""
            INSERT INTO sensor_readings
                (time, farm_id, field_id, device_id, sensor_type_id,
                 value, quality_flag, metadata)
            VALUES
                (:time, :farm_id, :field_id, :device_id, :sensor_type_id,
                 :value, :quality_flag, :metadata)
            ON CONFLICT (time, farm_id, device_id, sensor_type_id)
            DO NOTHING
        """)
        result = await self.session.execute(stmt, readings)
        logger.info("sensor_bulk_insert", inserted=result.rowcount)
        return result.rowcount

    # ------------------------------------------------------------------
    # Read — latest values (for Digital Twin feed)
    # ------------------------------------------------------------------

    async def get_latest_by_farm(
        self, farm_id: str, hours: int = 1
    ) -> dict[str, dict[str, Any]]:
        """
        Return latest averaged sensor values per sensor code for a farm.
        Suitable for feeding the digital twin live view.
        """
        query = text("""
            SELECT
                st.code,
                avg(sr.value)   AS avg_value,
                max(sr.time)    AS last_time,
                st.unit
            FROM sensor_readings sr
            JOIN sensor_types st ON sr.sensor_type_id = st.id
            WHERE sr.farm_id     = :fid
              AND sr.time        > now() - make_interval(hours => :hrs)
              AND sr.quality_flag IN ('RAW', 'EKF_CORRECTED')
            GROUP BY st.code, st.unit
        """)
        result = await self.session.execute(
            query, {"fid": str(farm_id), "hrs": hours}
        )
        return {
            row.code: {
                "value": float(row.avg_value) if row.avg_value is not None else None,
                "unit": row.unit,
                "updated_at": row.last_time,
            }
            for row in result
        }

    # ------------------------------------------------------------------
    # Read — time-bucketed aggregation (for charts)
    # ------------------------------------------------------------------

    async def get_time_series(
        self,
        farm_id: str,
        sensor_codes: list[str],
        start: datetime,
        end: datetime,
        interval: str = "15 minutes",
    ) -> list[dict[str, Any]]:
        """
        Return time-bucketed (avg/min/max) sensor readings for chart rendering.
        sensor_codes and interval are validated against allowlists.
        """
        codes = _validate_codes(sensor_codes)
        ivl = _validate_interval(interval)

        # Build parameterised IN clause
        placeholders = ", ".join(f":code_{i}" for i in range(len(codes)))
        params: dict[str, Any] = {
            "fid": str(farm_id),
            "start": start,
            "end": end,
        }
        for i, code in enumerate(codes):
            params[f"code_{i}"] = code

        query = text(f"""
            SELECT
                time_bucket('{ivl}', sr.time) AS bucket,
                st.code,
                avg(sr.value)   AS avg_value,
                min(sr.value)   AS min_value,
                max(sr.value)   AS max_value,
                count(*)        AS sample_count,
                st.unit
            FROM sensor_readings sr
            JOIN sensor_types st ON sr.sensor_type_id = st.id
            WHERE sr.farm_id      = :fid
              AND sr.time        BETWEEN :start AND :end
              AND st.code        IN ({placeholders})
              AND sr.quality_flag IN ('RAW', 'EKF_CORRECTED')
            GROUP BY bucket, st.code, st.unit
            ORDER BY bucket ASC, st.code
        """)
        result = await self.session.execute(query, params)
        return [dict(row._mapping) for row in result]

    # ------------------------------------------------------------------
    # Read — per device (for edge diagnostics)
    # ------------------------------------------------------------------

    async def get_device_health(
        self, device_id: str, minutes: int = 60
    ) -> dict[str, Any]:
        """Return recent reading count and last_seen for a device."""
        query = text("""
            SELECT
                count(*)        AS reading_count,
                max(time)       AS last_seen,
                min(value)      AS min_val,
                max(value)      AS max_val
            FROM sensor_readings
            WHERE device_id = :did
              AND time > now() - make_interval(mins => :mins)
        """)
        result = await self.session.execute(
            query, {"did": str(device_id), "mins": minutes}
        )
        row = result.one()
        return dict(row._mapping)
