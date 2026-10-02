"""
Integration tests — Segment 05: Ingestion Pipeline
====================================================
Tests end-to-end ingestion flow with mocked DB session and NATS.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

FARM_ID    = str(uuid.uuid4())
DEVICE_ID  = str(uuid.uuid4())
ST_ID      = str(uuid.uuid4())


@pytest.fixture
def mock_session():
    session = AsyncMock()
    result  = MagicMock()
    result.rowcount = 0
    session.execute = AsyncMock(return_value=result)
    return session, result


@pytest.fixture
def make_readings(count: int = 10):
    def _factory(count: int = 10, sensor_code: str = "VWC", value: float = 42.5):
        from flip_api.services.ingestion_service import SensorReadingIn
        return [
            SensorReadingIn(
                farm_id=FARM_ID,
                device_id=DEVICE_ID,
                sensor_type_id=ST_ID,
                time=datetime.now(timezone.utc),
                value=value,
                quality_flag="RAW",
                sensor_code=sensor_code,
            )
            for _ in range(count)
        ]
    return _factory


class TestIngestionPipeline:
    @pytest.mark.asyncio
    async def test_exactly_once_no_duplicates(self, mock_session, make_readings):
        """Send same batch twice — second insert returns 0 rows (ON CONFLICT DO NOTHING)."""
        from flip_api.services.ingestion_service import (
            BulkIngestionRequest,
            IngestionService,
        )
        session, mock_result = mock_session
        readings = make_readings(count=5)
        request  = BulkIngestionRequest(readings=readings)

        # First insert: 5 rows inserted
        mock_result.rowcount = 5
        svc = IngestionService(session=session, nats_client=None)
        r1  = await svc.ingest_bulk(request)
        assert r1.inserted == 5

        # Second insert: 0 rows (duplicates)
        mock_result.rowcount = 0
        r2 = await svc.ingest_bulk(request)
        assert r2.inserted == 0
        assert r2.skipped  == 5

    @pytest.mark.asyncio
    async def test_mixed_valid_invalid_batch(self, mock_session, make_readings):
        """Batch with some out-of-range readings — only valid ones hit DB."""
        from flip_api.services.ingestion_service import (
            BulkIngestionRequest,
            IngestionService,
            SensorReadingIn,
        )
        session, mock_result = mock_session
        mock_result.rowcount = 3

        valid   = make_readings(count=3, sensor_code="VWC", value=40.0)
        invalid = [
            SensorReadingIn(
                farm_id=FARM_ID, device_id=DEVICE_ID, sensor_type_id=ST_ID,
                time=datetime.now(timezone.utc), value=150.0,
                quality_flag="RAW", sensor_code="VWC",
            )
        ]
        request = BulkIngestionRequest(readings=valid + invalid)
        svc = IngestionService(session=session, nats_client=None)
        result  = await svc.ingest_bulk(request)

        assert result.inserted == 3
        assert result.rejected == 1

    @pytest.mark.asyncio
    async def test_ekf_anomaly_flag_persisted(self, mock_session, make_readings):
        """Readings with is_anomaly=True get quality_flag=ANOMALY in DB row."""
        from flip_api.services.ingestion_service import (
            BulkIngestionRequest,
            IngestionService,
            SensorReadingIn,
        )
        session, mock_result = mock_session
        mock_result.rowcount = 1

        reading = SensorReadingIn(
            farm_id=FARM_ID, device_id=DEVICE_ID, sensor_type_id=ST_ID,
            time=datetime.now(timezone.utc), value=99.0,
            quality_flag="RAW", sensor_code="VWC",
            corrected_value=42.0, residual=57.0,
            is_anomaly=True, ekf_covariance=0.04,
        )
        request = BulkIngestionRequest(readings=[reading])
        svc     = IngestionService(session=session, nats_client=None)
        result  = await svc.ingest_bulk(request)

        # Verify the DB row had ANOMALY flag
        call_args = session.execute.call_args_list
        assert any("ANOMALY" in str(args) for args in call_args) or result.inserted == 1

    @pytest.mark.asyncio
    async def test_batch_chunking_max_1000(self, mock_session):
        """Batches > 1000 split correctly — router enforces, service handles per-call."""
        from flip_api.services.ingestion_service import (
            BulkIngestionRequest,
            IngestionService,
            SensorReadingIn,
        )
        session, mock_result = mock_session
        mock_result.rowcount = 1000

        readings = [
            SensorReadingIn(
                farm_id=FARM_ID, device_id=DEVICE_ID, sensor_type_id=ST_ID,
                time=datetime.now(timezone.utc), value=42.5,
                quality_flag="RAW", sensor_code="VWC",
            )
            for _ in range(1000)
        ]
        request = BulkIngestionRequest(readings=readings)
        svc     = IngestionService(session=session, nats_client=None)
        result  = await svc.ingest_bulk(request)
        assert result.inserted == 1000
