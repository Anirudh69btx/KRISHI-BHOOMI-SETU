"""
Unit tests — Segment 05: EKF Anomaly Detection
===============================================
Tests all four physics EKF models plus the EKFModelSet registry.
No external dependencies — pure numpy math.
"""
from __future__ import annotations

import math
import numpy as np
import pytest


class TestEKFBase:
    """Test EKFBase predict/update mechanics via TempAirEKF."""

    def test_step_returns_required_keys(self):
        from edge.gateway.services.ekf_anomaly import TempAirEKF
        ekf = TempAirEKF(initial_value=28.0)
        result = ekf.step(28.5)
        assert "corrected_value" in result
        assert "residual" in result
        assert "is_anomaly" in result
        assert "quality_flag" in result
        assert "ekf_covariance" in result

    def test_small_perturbation_not_anomaly(self):
        from edge.gateway.services.ekf_anomaly import TempAirEKF
        ekf = TempAirEKF(initial_value=25.0, dt=60.0)
        # Warm up 10 steps
        for _ in range(10):
            ekf.step(25.0 + np.random.normal(0, 0.1))
        result = ekf.step(25.2)   # tiny change
        assert result["is_anomaly"] is False
        assert result["quality_flag"] == "EKF_CORRECTED"

    def test_large_spike_is_anomaly(self):
        from edge.gateway.services.ekf_anomaly import TempAirEKF
        ekf = TempAirEKF(initial_value=25.0, dt=60.0)
        # Converge model
        for _ in range(20):
            ekf.step(25.0)
        # Inject impossible spike
        result = ekf.step(80.0)
        assert result["is_anomaly"] is True
        assert result["quality_flag"] == "ANOMALY"

    def test_corrected_value_in_range(self):
        from edge.gateway.services.ekf_anomaly import TempAirEKF
        ekf = TempAirEKF(initial_value=30.0)
        for val in [30.1, 30.2, 29.9, 30.0]:
            r = ekf.step(val)
            # corrected value should stay near 30
            assert abs(r["corrected_value"] - 30.0) < 5.0

    def test_covariance_decreases_over_time(self):
        from edge.gateway.services.ekf_anomaly import RH_EKF
        try:
            from edge.gateway.services.ekf_anomaly import RHEKF
        except ImportError:
            from edge.gateway.services.ekf_anomaly import RHEKF
        ekf = RHEKF(initial_value=65.0)
        cov_initial = ekf.state.P[0, 0]
        for _ in range(30):
            ekf.step(65.0 + np.random.normal(0, 0.5))
        cov_final = ekf.state.P[0, 0]
        assert cov_final < cov_initial


class TestTempSoilEKF:
    def test_basic_step(self):
        from edge.gateway.services.ekf_anomaly import TempSoilEKF
        ekf = TempSoilEKF(initial_value=22.0)
        r = ekf.step(22.3, u=25.0)   # u = air temp control input
        assert isinstance(r["corrected_value"], float)
        assert isinstance(r["residual"], float)

    def test_stable_sequence(self):
        from edge.gateway.services.ekf_anomaly import TempSoilEKF
        ekf = TempSoilEKF(initial_value=24.0, dt=60.0)
        for _ in range(20):
            r = ekf.step(24.0 + np.random.normal(0, 0.2), u=26.0)
        assert not r["is_anomaly"]


class TestVWCEKF:
    def test_basic_step(self):
        from edge.gateway.services.ekf_anomaly import VWCEKF
        ekf = VWCEKF(initial_value=35.0)
        r = ekf.step(35.5, u=0.0)
        assert r["corrected_value"] >= 0.0
        assert r["corrected_value"] <= 100.0

    def test_sudden_vwc_drop_is_anomaly(self):
        from edge.gateway.services.ekf_anomaly import VWCEKF
        ekf = VWCEKF(initial_value=40.0, dt=60.0)
        for _ in range(20):
            ekf.step(40.0)
        result = ekf.step(5.0)  # sudden drainage anomaly
        assert result["is_anomaly"] is True


class TestRHEKF:
    def test_rh_clipped_to_100(self):
        from edge.gateway.services.ekf_anomaly import RHEKF
        ekf = RHEKF(initial_value=95.0)
        for _ in range(5):
            r = ekf.step(98.0)
        assert r["corrected_value"] <= 100.0

    def test_rh_clipped_to_zero(self):
        from edge.gateway.services.ekf_anomaly import RHEKF
        ekf = RHEKF(initial_value=5.0)
        r = ekf.step(0.0)
        assert r["corrected_value"] >= 0.0


class TestEKFModelSet:
    def test_process_known_sensor(self):
        from edge.gateway.services.ekf_anomaly import EKFModelSet
        ekfs = EKFModelSet(dt=60.0)
        r = ekfs.process("device-001", "VWC", 35.0)
        assert "quality_flag" in r
        assert "corrected_value" in r

    def test_process_unknown_sensor_passthrough(self):
        from edge.gateway.services.ekf_anomaly import EKFModelSet
        ekfs = EKFModelSet()
        r = ekfs.process("device-001", "MYSTERY_SENSOR", 42.0)
        assert r["corrected_value"] == 42.0
        assert r["is_anomaly"] is False
        assert r["quality_flag"] == "RAW"

    def test_model_persists_between_calls(self):
        from edge.gateway.services.ekf_anomaly import EKFModelSet
        ekfs = EKFModelSet(dt=60.0)
        # First call creates model
        r1 = ekfs.process("device-001", "TEMP_AIR", 25.0)
        # Second call uses same model (should not reset state)
        r2 = ekfs.process("device-001", "TEMP_AIR", 25.1)
        assert r1["ekf_covariance"] != r2["ekf_covariance"]

    def test_different_devices_independent(self):
        from edge.gateway.services.ekf_anomaly import EKFModelSet
        ekfs = EKFModelSet(dt=60.0)
        for _ in range(20):
            ekfs.process("device-A", "TEMP_AIR", 25.0)
        for _ in range(20):
            ekfs.process("device-B", "TEMP_AIR", 40.0)
        # device-A should detect 60°C as anomaly
        r = ekfs.process("device-A", "TEMP_AIR", 60.0)
        assert r["is_anomaly"] is True

    def test_reset_clears_model(self):
        from edge.gateway.services.ekf_anomaly import EKFModelSet
        ekfs = EKFModelSet(dt=60.0)
        ekfs.process("device-001", "VWC", 35.0)
        assert ("device-001", "VWC") in ekfs._models
        ekfs.reset("device-001", "VWC")
        assert ("device-001", "VWC") not in ekfs._models

    def test_all_four_sensors_supported(self):
        from edge.gateway.services.ekf_anomaly import EKFModelSet, EKF_REGISTRY
        assert "TEMP_SOIL" in EKF_REGISTRY
        assert "TEMP_AIR"  in EKF_REGISTRY
        assert "VWC"       in EKF_REGISTRY
        assert "RH"        in EKF_REGISTRY
