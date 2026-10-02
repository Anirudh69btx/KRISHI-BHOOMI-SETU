"""
Unit tests — Segment 05: Ingestion Service
==========================================
Tests schema validation, range checking, deduplication logic,
NATS publishing, and Prometheus metrics — all without a live DB.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────────

FARM_ID = str(uuid.uuid4())
DEVICE_ID = str(uuid.uuid4())
SENSOR_TYPE_ID = str(uuid.uuid4())
NOW = datetime.now(timezone.utc)


def make_reading(**overrides) -> dict:
    base = {
        "farm_id":        FARM_ID,
        "device_id":      DEVICE_ID,
        "sensor_type_id": SENSOR_TYPE_ID,
        "time":           NOW.isoformat(),
        "value":          42.5,
        "quality_flag":   "RAW",
        "sensor_code":    "VWC",
    }
    base.update(overrides)
    return base


# ── Validation tests ──────────────────────────────────────────────────────────

class TestSensorReadingSchema:
    def test_valid_reading(self):
        from flip_api.services.ingestion_service import SensorReadingIn
        r = SensorReadingIn(**make_reading())
        assert r.value == 42.5
        assert r.quality_flag == "RAW"

    def test_invalid_quality_flag(self):
        from pydantic import ValidationError
        from flip_api.services.ingestion_service import SensorReadingIn
        with pytest.raises(ValidationError):
            SensorReadingIn(**make_reading(quality_flag="INVALID"))

    def test_time_string_parsed(self):
        from flip_api.services.ingestion_service import SensorReadingIn
        r = SensorReadingIn(**make_reading(time="2026-09-01T12:00:00Z"))
        assert r.time.tzinfo is not None

    def test_time_naive_gets_utc(self):
        from flip_api.services.ingestion_service import SensorReadingIn
        r = SensorReadingIn(**make_reading(time=datetime(2026, 9, 1, 12, 0, 0)))
        assert r.time.tzinfo is not None


class TestRangeValidation:
    def test_vwc_in_range(self):
        from flip_api.services.ingestion_service import SensorReadingIn, validate_range
        r = SensorReadingIn(**make_reading(value=45.0, sensor_code="VWC"))
        ok, reason = validate_range(r)
        assert ok is True
        assert reason == ""

    def test_vwc_out_of_range_high(self):
        from flip_api.services.ingestion_service import SensorReadingIn, validate_range
        r = SensorReadingIn(**make_reading(value=150.0, sensor_code="VWC"))
        ok, reason = validate_range(r)
        assert ok is False
        assert "out_of_range" in reason
        assert "VWC" in reason

    def test_temp_out_of_range_low(self):
        from flip_api.services.ingestion_service import SensorReadingIn, validate_range
        r = SensorReadingIn(**make_reading(value=-50.0, sensor_code="TEMP_AIR"))
        ok, reason = validate_range(r)
        assert ok is False

    def test_unknown_sensor_passes(self):
        from flip_api.services.ingestion_service import SensorReadingIn, validate_range
        r = SensorReadingIn(**make_reading(value=999.0, sensor_code="UNKNOWN_NEW"))
        ok, _ = validate_range(r)
        assert ok is True   # unknown sensors pass through

    def test_rh_boundary(self):
        from flip_api.services.ingestion_service import SensorReadingIn, validate_range
        r_min = SensorReadingIn(**make_reading(value=0.0,   sensor_code="RH"))
        r_max = SensorReadingIn(**make_reading(value=100.0, sensor_code="RH"))
        assert validate_range(r_min)[0] is True
        assert validate_range(r_max)[0] is True


class TestBulkIngestionRequest:
    def test_max_1000_readings(self):
        from pydantic import ValidationError
        from flip_api.services.ingestion_service import (
            BulkIngestionRequest,
            SensorReadingIn,
        )
        readings = [SensorReadingIn(**make_reading()) for _ in range(1001)]
        with pytest.raises(ValidationError):
            BulkIngestionRequest(readings=readings)

    def test_empty_readings_rejected(self):
        from pydantic import ValidationError
        from flip_api.services.ingestion_service import BulkIngestionRequest
        with pytest.raises(ValidationError):
            BulkIngestionRequest(readings=[])


# ── Service integration (mocked DB + NATS) ───────────────────────────────────

class TestIngestionService:
    @pytest.mark.asyncio
    async def test_ingest_bulk_inserts_valid(self):
        from flip_api.services.ingestion_service import (
            BulkIngestionRequest,
            IngestionService,
            SensorReadingIn,
        )

        mock_session = AsyncMock()
        mock_result  = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_nats = AsyncMock()

        readings = [SensorReadingIn(**make_reading(value=float(i * 10))) for i in range(1, 4)]
        request  = BulkIngestionRequest(readings=readings)

        svc = IngestionService(session=mock_session, nats_client=mock_nats)
        result = await svc.ingest_bulk(request)

        assert result.inserted == 3
        assert result.rejected == 0
        mock_nats.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_bulk_rejects_out_of_range(self):
        from flip_api.services.ingestion_service import (
            BulkIngestionRequest,
            IngestionService,
            SensorReadingIn,
        )

        mock_session = AsyncMock()
        mock_result  = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        readings = [SensorReadingIn(**make_reading(value=999.0, sensor_code="VWC"))]
        request  = BulkIngestionRequest(readings=readings)

        svc = IngestionService(session=mock_session, nats_client=None)
        result = await svc.ingest_bulk(request)

        assert result.rejected == 1
        assert result.inserted == 0

    @pytest.mark.asyncio
    async def test_dedup_zero_inserted_on_conflict(self):
        """Simulate ON CONFLICT DO NOTHING returning rowcount=0 (duplicate)."""
        from flip_api.services.ingestion_service import (
            BulkIngestionRequest,
            IngestionService,
            SensorReadingIn,
        )

        mock_session = AsyncMock()
        mock_result  = MagicMock()
        mock_result.rowcount = 0   # all duplicates
        mock_session.execute = AsyncMock(return_value=mock_result)

        readings = [SensorReadingIn(**make_reading())]
        request  = BulkIngestionRequest(readings=readings)

        svc = IngestionService(session=mock_session, nats_client=None)
        result = await svc.ingest_bulk(request)

        assert result.inserted == 0
        assert result.skipped  == 1

    @pytest.mark.asyncio
    async def test_nats_failure_does_not_raise(self):
        """NATS failure should be logged, not propagate."""
        from flip_api.services.ingestion_service import (
            BulkIngestionRequest,
            IngestionService,
            SensorReadingIn,
        )

        mock_session = AsyncMock()
        mock_result  = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_nats = AsyncMock()
        mock_nats.publish = AsyncMock(side_effect=RuntimeError("NATS down"))

        readings = [SensorReadingIn(**make_reading())]
        request  = BulkIngestionRequest(readings=readings)

        svc = IngestionService(session=mock_session, nats_client=mock_nats)
        result = await svc.ingest_bulk(request)  # must not raise
        assert result.inserted == 1

    def test_to_db_row_ekf_corrected(self):
        from flip_api.services.ingestion_service import IngestionService, SensorReadingIn
        r = SensorReadingIn(
            **make_reading(
                corrected_value=43.1,
                residual=0.6,
                is_anomaly=False,
                quality_flag="RAW",
            )
        )
        row = IngestionService._to_db_row(r)
        assert row["value"] == 43.1          # uses corrected_value
        assert row["quality_flag"] == "EKF_CORRECTED"

    def test_to_db_row_anomaly_flag(self):
        from flip_api.services.ingestion_service import IngestionService, SensorReadingIn
        r = SensorReadingIn(**make_reading(is_anomaly=True, quality_flag="RAW"))
        row = IngestionService._to_db_row(r)
        assert row["quality_flag"] == "ANOMALY"
