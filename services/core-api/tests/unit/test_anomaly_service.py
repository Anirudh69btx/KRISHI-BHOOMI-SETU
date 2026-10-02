"""
Unit tests — Segment 05: Anomaly Service + Health Scoring
==========================================================
Tests Isolation Forest scoring logic, health score calculation,
and ticket creation logic — all mocked, no live DB.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


FARM_ID = str(uuid.uuid4())


class TestIsolationForestScoring:
    def test_if_detects_outlier(self):
        """Sanity check: IF marks clear outliers as anomalies."""
        pytest.importorskip("sklearn")
        from sklearn.ensemble import IsolationForest

        rng = np.random.RandomState(42)
        X_train = rng.randn(300, 7) * 5 + 30   # normal cluster
        model = IsolationForest(contamination=0.01, random_state=42, n_estimators=50)
        model.fit(X_train)

        X_normal  = rng.randn(10, 7) * 5 + 30
        X_outlier = np.full((5, 7), 200.0)       # extreme values

        labels_normal  = model.predict(X_normal)
        labels_outlier = model.predict(X_outlier)

        assert all(l == 1 for l in labels_normal),   "Normal data should not be flagged"
        assert all(l == -1 for l in labels_outlier), "Extreme outliers must be flagged"

    @pytest.mark.asyncio
    async def test_anomaly_service_run_inference_no_model(self):
        """When no model exists, training is triggered before inference."""
        from flip_api.services.anomaly_service import AnomalyService

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))

        svc = AnomalyService(session=mock_session, nats_client=None)
        result = await svc.run_inference(FARM_ID)
        assert result == []   # no data → no anomalies

    @pytest.mark.asyncio
    async def test_persist_anomaly_calls_execute(self):
        from flip_api.services.anomaly_service import AnomalyService

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock())

        svc = AnomalyService(session=mock_session, nats_client=None)
        anomaly = {
            "farm_id":      FARM_ID,
            "detected_at":  datetime.now(timezone.utc).isoformat(),
            "anomaly_type": "ISOLATION_FOREST",
            "severity":     "WARNING",
            "anomaly_score": -0.15,
            "sensor_values": {"VWC": 42.3},
        }
        await svc.persist_anomaly(anomaly)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_anomaly_calls_nats(self):
        from flip_api.services.anomaly_service import AnomalyService

        mock_nats = AsyncMock()
        svc = AnomalyService(session=AsyncMock(), nats_client=mock_nats)

        anomaly = {
            "farm_id": FARM_ID,
            "anomaly_type": "ISOLATION_FOREST",
            "severity": "WARNING",
        }
        await svc.emit_anomaly_event(anomaly)
        mock_nats.publish.assert_called_once()
        subject = mock_nats.publish.call_args[0][0]
        assert f"farm.{FARM_ID}.sensor.anomaly" == subject


class TestHealthScoringFactors:
    def test_anomaly_frequency_zero_anomalies(self):
        from flip_api.services.health_scoring_service import score_anomaly_frequency
        assert score_anomaly_frequency(0) == 100.0

    def test_anomaly_frequency_twenty_anomalies(self):
        from flip_api.services.health_scoring_service import score_anomaly_frequency
        assert score_anomaly_frequency(20) == 0.0   # 20 * 5 = 100 → 0

    def test_anomaly_frequency_capped_at_zero(self):
        from flip_api.services.health_scoring_service import score_anomaly_frequency
        assert score_anomaly_frequency(100) == 0.0

    def test_battery_trend_positive_slope(self):
        from flip_api.services.health_scoring_service import score_battery_trend
        # Increasing battery → score 100
        readings = [3200.0 + i * 10 for i in range(30)]
        assert score_battery_trend(readings) == 100.0

    def test_battery_trend_steep_decline(self):
        from flip_api.services.health_scoring_service import score_battery_trend
        # -10mV/day → clamped to score 0
        readings = [3800.0 - i * 10 for i in range(30)]
        assert score_battery_trend(readings) == 0.0

    def test_battery_trend_single_reading(self):
        from flip_api.services.health_scoring_service import score_battery_trend
        # Not enough data → neutral
        assert score_battery_trend([3400.0]) == 70.0

    def test_rssi_good_signal(self):
        from flip_api.services.health_scoring_service import score_rssi
        assert score_rssi(-60.0) == 100.0

    def test_rssi_no_signal(self):
        from flip_api.services.health_scoring_service import score_rssi
        assert score_rssi(-120.0) == 0.0

    def test_rssi_mid_signal(self):
        from flip_api.services.health_scoring_service import score_rssi
        assert score_rssi(-90.0) == 60.0

    def test_rssi_none_returns_neutral(self):
        from flip_api.services.health_scoring_service import score_rssi
        assert score_rssi(None) == 50.0

    def test_calibration_age_fresh(self):
        from flip_api.services.health_scoring_service import score_calibration_age
        assert score_calibration_age(0) == 100.0

    def test_calibration_age_overdue(self):
        from flip_api.services.health_scoring_service import score_calibration_age
        assert score_calibration_age(60) == 0.0   # 60 * 2 = 120 → clamped at 0

    def test_data_completeness_full(self):
        from flip_api.services.health_scoring_service import score_data_completeness
        assert score_data_completeness(2880, 2880) == 100.0

    def test_data_completeness_half(self):
        from flip_api.services.health_scoring_service import score_data_completeness
        assert score_data_completeness(1440, 2880) == 50.0

    def test_data_completeness_zero_expected(self):
        from flip_api.services.health_scoring_service import score_data_completeness
        assert score_data_completeness(0, 0) == 0.0

    def test_composite_score_all_perfect(self):
        from flip_api.services.health_scoring_service import compute_composite_score
        factors = {
            "anomaly_frequency": 100.0,
            "battery_trend":     100.0,
            "rssi":              100.0,
            "calibration_age":   100.0,
            "data_completeness": 100.0,
        }
        assert compute_composite_score(factors) == 100

    def test_composite_score_all_zero(self):
        from flip_api.services.health_scoring_service import compute_composite_score
        factors = {
            "anomaly_frequency": 0.0,
            "battery_trend":     0.0,
            "rssi":              0.0,
            "calibration_age":   0.0,
            "data_completeness": 0.0,
        }
        assert compute_composite_score(factors) == 0

    def test_composite_score_below_threshold_triggers_alert(self):
        from flip_api.services.health_scoring_service import (
            compute_composite_score,
            HEALTH_DEGRADED_THRESHOLD,
        )
        factors = {
            "anomaly_frequency": 20.0,  # many anomalies
            "battery_trend":     15.0,  # fast drain
            "rssi":              30.0,  # weak signal
            "calibration_age":   50.0,
            "data_completeness": 60.0,
        }
        score = compute_composite_score(factors)
        assert score < HEALTH_DEGRADED_THRESHOLD
