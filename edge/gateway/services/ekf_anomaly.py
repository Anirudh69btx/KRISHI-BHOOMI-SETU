"""
FLIP Core API — Segment 05: Edge EKF Anomaly Detection
======================================================
Extended Kalman Filter (EKF) per-sensor physics models.
Runs on the Pi Zero 2W gateway for every sensor reading,
before MQTT/NATS publish.

Supported sensors:
  • TEMP_SOIL  — Newtonian soil heat balance
  • TEMP_AIR   — Newtonian cooling + solar forcing
  • VWC        — Soil water balance (rain + irrigation - ET - drainage)
  • RH         — Psychrometric + advection model

Output per reading:
  {
    "corrected_value": float,
    "residual":        float,
    "is_anomaly":      bool,
    "quality_flag":    str,     # "RAW" | "EKF_CORRECTED" | "ANOMALY"
    "ekf_covariance":  float,
  }

Anomaly threshold: |residual| > 3 * sqrt(P + R)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

# ── EKF Base ──────────────────────────────────────────────────────────────────

@dataclass
class EKFState:
    """Minimal EKF state container."""
    x: np.ndarray          # state vector  [value, d_value/dt]
    P: np.ndarray          # error covariance matrix (2x2)
    Q: np.ndarray          # process noise covariance (2x2)
    R: float               # measurement noise variance
    dt: float = 1.0        # time step (seconds between readings)


class EKFBase:
    """
    Generic discrete-time Extended Kalman Filter.
    Subclasses implement:
      - f(x, u)  → predicted state x_pred
      - F(x, u)  → Jacobian of f (linearization)
    Measurement model: z = Hx + noise, H = [1, 0]
    """
    H = np.array([[1.0, 0.0]])   # measurement matrix — observe first state only

    def __init__(self, initial_value: float, state: EKFState):
        self.state = state
        self.state.x = np.array([initial_value, 0.0])
        # Initialize P with higher prior uncertainty so filter converges downward
        self.state.P = np.eye(2) * 10.0

    def predict(self, u: Optional[float] = None) -> None:
        """EKF prediction step."""
        x = self.state.x
        F = self._jacobian(x, u)
        x_pred = self._dynamics(x, u)
        P_pred = F @ self.state.P @ F.T + self.state.Q
        self.state.x = x_pred
        self.state.P = P_pred

    def update(self, z: float) -> dict:
        """
        EKF update step.
        Returns anomaly result dict.
        """
        x = self.state.x
        P = self.state.P
        H = self.H
        R = self.state.R

        # Innovation / residual
        y = z - float((H @ x)[0])
        S = float((H @ P @ H.T)[0, 0]) + R  # innovation covariance
        K = (P @ H.T) / S                    # Kalman gain

        # State update
        self.state.x = x + K.flatten() * y
        self.state.P = (np.eye(2) - np.outer(K.flatten(), H)) @ P

        # Anomaly detection: |y| > 3σ
        sigma = math.sqrt(max(S, 1e-9))
        is_anomaly = abs(y) > 3.0 * sigma

        quality_flag = "ANOMALY" if is_anomaly else "EKF_CORRECTED"

        return {
            "corrected_value": float(self.state.x[0]),
            "residual":        round(y, 6),
            "is_anomaly":      is_anomaly,
            "quality_flag":    quality_flag,
            "ekf_covariance":  round(float(self.state.P[0, 0]), 6),
            "innovation_sigma": round(sigma, 6),
        }

    def step(self, z: float, u: Optional[float] = None) -> dict:
        """Convenience: predict → update in one call."""
        self.predict(u)
        return self.update(z)

    def _dynamics(self, x: np.ndarray, u: Optional[float]) -> np.ndarray:
        raise NotImplementedError

    def _jacobian(self, x: np.ndarray, u: Optional[float]) -> np.ndarray:
        raise NotImplementedError


# ── Sensor-Specific EKF Models ────────────────────────────────────────────────

class TempSoilEKF(EKFBase):
    """
    Soil temperature EKF.
    Physics: dT_soil/dt = (T_air - T_soil)/τ + α·PAR - β·ETc
    State:   [T_soil, dT_soil/dt]
    Q:       diag(0.01, 0.001)
    R:       0.5°C
    τ = 3600s (soil thermal relaxation time constant)
    """
    TAU = 3600.0      # seconds — soil thermal time constant
    ALPHA = 0.002 / 3600.0  # PAR heating coefficient (scaled to s^-1)
    BETA = 0.001 / 3600.0   # ETc cooling coefficient (scaled to s^-1)

    def __init__(self, initial_value: float, dt: float = 60.0):
        state = EKFState(
            x=np.zeros(2),
            P=np.eye(2),
            Q=np.diag([0.01, 0.001]),
            R=0.5,
            dt=dt,
        )
        super().__init__(initial_value, state)

    def _dynamics(self, x: np.ndarray, u: Optional[float]) -> np.ndarray:
        t_soil, dt_dt = x
        t_air = u if u is not None else t_soil  # fallback
        par = 0.0  # solar radiation (u provides air temp by default)
        d_t_soil = (t_air - t_soil) / self.TAU + self.ALPHA * par
        new_t_soil = t_soil + d_t_soil * self.state.dt
        new_dt_dt = d_t_soil
        return np.array([new_t_soil, new_dt_dt])

    def _jacobian(self, x: np.ndarray, u: Optional[float]) -> np.ndarray:
        dt = self.state.dt
        return np.array([
            [1.0 - dt / self.TAU,  dt],
            [-1.0 / self.TAU,       0.0],
        ])


class TempAirEKF(EKFBase):
    """
    Air temperature EKF.
    Physics: Newtonian cooling + solar forcing
    State:   [T_air, dT_air/dt]
    Q:       diag(0.05, 0.01)
    R:       0.3°C
    """
    TAU = 7200.0  # 2h atmospheric thermal relaxation

    def __init__(self, initial_value: float, dt: float = 60.0):
        state = EKFState(
            x=np.zeros(2),
            P=np.eye(2),
            Q=np.diag([0.05, 0.01]),
            R=0.3,
            dt=dt,
        )
        super().__init__(initial_value, state)

    def _dynamics(self, x: np.ndarray, u: Optional[float]) -> np.ndarray:
        t_air, d_t = x
        t_ref = u if u is not None else t_air
        d_dt = (t_ref - t_air) / self.TAU
        return np.array([t_air + d_dt * self.state.dt, d_dt])

    def _jacobian(self, x: np.ndarray, u: Optional[float]) -> np.ndarray:
        dt = self.state.dt
        return np.array([
            [1.0 - dt / self.TAU, dt],
            [-1.0 / self.TAU,      0.0],
        ])


class VWCEKF(EKFBase):
    """
    Volumetric Water Content EKF.
    Physics: dθ/dt = (Rain + Irrigation - ETc - Drainage) / Depth
    State:   [θ, dθ/dt]
    Q:       diag(0.001, 0.0001)
    R:       1.0%
    Depth = 300mm, ETc = 3mm/day default
    """
    DEPTH_MM = 300.0
    ETC_MM_PER_SEC = 3.0 / 86400.0  # 3mm/day default ETc

    def __init__(self, initial_value: float, dt: float = 60.0):
        state = EKFState(
            x=np.zeros(2),
            P=np.eye(2),
            Q=np.diag([0.001, 0.0001]),
            R=1.0,
            dt=dt,
        )
        super().__init__(initial_value, state)

    def _dynamics(self, x: np.ndarray, u: Optional[float]) -> np.ndarray:
        theta, d_theta = x
        rain_mm_s = u / self.DEPTH_MM if u is not None else 0.0
        net = rain_mm_s - self.ETC_MM_PER_SEC
        new_theta = theta + net * self.state.dt
        new_theta = float(np.clip(new_theta, 0.0, 100.0))
        return np.array([new_theta, net])

    def _jacobian(self, x: np.ndarray, u: Optional[float]) -> np.ndarray:
        return np.array([
            [1.0, self.state.dt],
            [0.0, 1.0],
        ])


class RHEKF(EKFBase):
    """
    Relative Humidity EKF.
    Physics: Psychrometric + advection model
    State:   [RH, dRH/dt]
    Q:       diag(0.5, 0.1)
    R:       2.0%
    """
    TAU_RH = 1800.0  # 30-min RH relaxation time

    def __init__(self, initial_value: float, dt: float = 60.0):
        state = EKFState(
            x=np.zeros(2),
            P=np.eye(2),
            Q=np.diag([0.5, 0.1]),
            R=2.0,
            dt=dt,
        )
        super().__init__(initial_value, state)

    def _dynamics(self, x: np.ndarray, u: Optional[float]) -> np.ndarray:
        rh, d_rh = x
        rh_target = u if u is not None else 65.0  # climatological RH
        d_dt = (rh_target - rh) / self.TAU_RH
        new_rh = float(np.clip(rh + d_dt * self.state.dt, 0.0, 100.0))
        return np.array([new_rh, d_dt])

    def _jacobian(self, x: np.ndarray, u: Optional[float]) -> np.ndarray:
        dt = self.state.dt
        return np.array([
            [1.0 - dt / self.TAU_RH, dt],
            [-1.0 / self.TAU_RH,      0.0],
        ])


# Alias for backwards compatibility
RH_EKF = RHEKF

# ── EKF Registry ─────────────────────────────────────────────────────────────

# Map sensor code → EKF class
EKF_REGISTRY: dict[str, type] = {
    "TEMP_SOIL": TempSoilEKF,
    "TEMP_AIR":  TempAirEKF,
    "VWC":       VWCEKF,
    "RH":        RHEKF,
}


class EKFModelSet:
    """
    Manages one EKF instance per sensor per device.
    Keyed by (device_id, sensor_code).
    Used by the gateway MQTT handler before NATS publish.
    """

    def __init__(self, dt: float = 60.0):
        self._models: dict[tuple[str, str], EKFBase] = {}
        self.dt = dt

    def _get_or_create(
        self, device_id: str, sensor_code: str, initial_value: float
    ) -> EKFBase:
        key = (device_id, sensor_code)
        if key not in self._models:
            cls = EKF_REGISTRY.get(sensor_code)
            if cls is None:
                return None  # type: ignore[return-value]
            self._models[key] = cls(initial_value=initial_value, dt=self.dt)
        return self._models[key]

    def process(
        self,
        device_id: str,
        sensor_code: str,
        value: float,
        control_input: Optional[float] = None,
    ) -> dict:
        """
        Run EKF predict+update for a single reading.
        Returns anomaly result dict.
        If no EKF model exists for this sensor, returns passthrough result.
        """
        ekf = self._get_or_create(device_id, sensor_code, value)
        if ekf is None:
            return {
                "corrected_value": value,
                "residual":        0.0,
                "is_anomaly":      False,
                "quality_flag":    "RAW",
                "ekf_covariance":  None,
            }
        return ekf.step(value, control_input)

    def reset(self, device_id: str, sensor_code: str) -> None:
        """Remove EKF state for a device-sensor pair (e.g. after calibration)."""
        self._models.pop((device_id, sensor_code), None)
