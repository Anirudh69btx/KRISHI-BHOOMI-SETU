"""
FLIP v3.0 — Python Domain Models & TypedDicts (synced with TypeScript types)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, Field


class SensorType(str, Enum):
    VWC = "VWC"
    EC = "EC"
    TEMP_SOIL = "TEMP_SOIL"
    TEMP_AIR = "TEMP_AIR"
    HUMIDITY = "HUMIDITY"
    LEAF_WETNESS = "LEAF_WETNESS"
    LIGHT_PAR = "LIGHT_PAR"
    WIND_SPEED = "WIND_SPEED"
    WIND_DIR = "WIND_DIR"
    RAIN_GAUGE = "RAIN_GAUGE"
    PRESSURE_ATM = "PRESSURE_ATM"
    CO2 = "CO2"
    NDVI = "NDVI"
    PH = "PH"
    NPK_N = "NPK_N"
    NPK_P = "NPK_P"
    NPK_K = "NPK_K"


class QualityFlag(str, Enum):
    VALID = "VALID"
    SUSPECT = "SUSPECT"
    OUT_OF_BOUNDS = "OUT_OF_BOUNDS"
    CALIBRATED = "CALIBRATED"
    INTERPOLATED = "INTERPOLATED"
    RAW = "RAW"


class SensorReading(BaseModel):
    time: datetime
    farm_id: UUID
    field_id: Optional[UUID] = None
    device_id: UUID
    sensor_type: SensorType
    value: float
    raw_value: Optional[float] = None
    quality_flag: QualityFlag = QualityFlag.VALID
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Advisory(BaseModel):
    id: str
    issued_at: datetime
    farm_id: UUID
    field_id: Optional[UUID] = None
    cycle_id: Optional[UUID] = None
    now_text: str
    next_text: str
    why_text: str
    prediction_set: List[str] = Field(default_factory=list)
    confidence_set: List[str] = Field(default_factory=list)
    coverage_target: float = 0.95
    coverage: float = 0.95
    risk_factors: Dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime
    verification_due: Optional[datetime] = None
    status: str = "ACTIVE"
    model_version: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DisasterAlert(BaseModel):
    id: str
    issued_at: datetime
    event_type: str
    severity: str
    expires_at: datetime
    message_template: Dict[str, Any]
    source: str
    status: str = "ACTIVE"
    sirens_triggered: bool = False
    ivr_dispatched: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
