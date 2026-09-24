"""
FLIP v3.0 — Core API REST Routers
Disaster router: active alerts, shelter map, SOS broadcast, drill simulation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from flip_api.auth.keycloak import get_current_user, require_roles
from flip_api.database import get_session
from flip_api.events.nats_client import get_nats

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/disaster", tags=["disaster"])


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class DisasterAlertResponse(BaseModel):
    id: str
    alert_type: str
    severity: str
    title: str
    title_local: Optional[dict] = None
    description: str
    description_local: Optional[dict] = None
    affected_districts: list[str]
    affected_states: list[str]
    evacuation_zones: list[str]
    shelter_locations: list[dict[str, Any]]
    source_agency: str
    issued_at: str
    expires_at: Optional[str] = None
    is_drill: bool


class SOSRequest(BaseModel):
    farm_id: uuid.UUID
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    message: Optional[str] = None
    contact_phone: Optional[str] = None


class DrillRequest(BaseModel):
    alert_type: str = "flood"
    severity: str = "high"
    affected_districts: list[str] = Field(default_factory=list)


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get(
    "/alerts",
    response_model=list[DisasterAlertResponse],
    summary="Get active disaster alerts",
)
async def get_active_alerts(
    district: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    include_expired: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    query = text("""
        SELECT
            id::text, alert_type, severity, title, title_local,
            description, description_local,
            affected_districts, affected_states, evacuation_zones,
            shelter_locations, source_agency,
            issued_at::text, expires_at::text, is_drill
        FROM disaster_alerts
        WHERE (:include_expired = true OR expires_at IS NULL OR expires_at > now())
          AND (:district IS NULL OR :district = ANY(affected_districts))
          AND (:state IS NULL OR :state = ANY(affected_states))
        ORDER BY
            CASE severity
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
            END,
            issued_at DESC
        LIMIT 20
    """)

    result = await session.execute(
        query,
        {
            "district": district,
            "state": state,
            "include_expired": include_expired,
        },
    )
    return [dict(r) for r in result.mappings().all()]


@router.get(
    "/shelters",
    summary="Get nearby shelter locations (PostGIS radius search)",
)
async def get_nearby_shelters(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    query = text("""
        SELECT
            id::text,
            name,
            address,
            capacity,
            current_occupancy,
            facilities,
            contact_phone,
            ST_Y(location::geometry) AS latitude,
            ST_X(location::geometry) AS longitude,
            ST_Distance(
                location::geography,
                ST_MakePoint(:lon, :lat)::geography
            ) / 1000 AS distance_km
        FROM emergency_shelters
        WHERE is_active = true
          AND ST_DWithin(
              location::geography,
              ST_MakePoint(:lon, :lat)::geography,
              :radius_m
          )
        ORDER BY distance_km ASC
        LIMIT 20
    """)

    result = await session.execute(
        query,
        {"lat": latitude, "lon": longitude, "radius_m": radius_km * 1000},
    )
    return [dict(r) for r in result.mappings().all()]


@router.post(
    "/sos",
    status_code=status.HTTP_201_CREATED,
    summary="Broadcast SOS from farmer",
)
async def send_sos(
    sos: SOSRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
    nats=Depends(get_nats),
) -> dict:
    sos_id = uuid.uuid4()

    # Persist SOS record
    await session.execute(
        text("""
            INSERT INTO sos_events
                (id, farm_id, farmer_id, location, message, contact_phone, sent_at)
            VALUES
                (:id, :farm_id, :farmer_id,
                 ST_MakePoint(:lon, :lat)::geography,
                 :message, :phone, now())
        """),
        {
            "id": str(sos_id),
            "farm_id": str(sos.farm_id),
            "farmer_id": current_user.get("farmer_id"),
            "lat": sos.latitude,
            "lon": sos.longitude,
            "message": sos.message,
            "phone": sos.contact_phone,
        },
    )
    await session.commit()

    # Publish to NATS for real-time broadcast
    import json
    await nats.publish(
        subject="disaster.sos",
        payload=json.dumps({
            "sos_id": str(sos_id),
            "farm_id": str(sos.farm_id),
            "farmer_id": current_user.get("farmer_id"),
            "lat": sos.latitude,
            "lon": sos.longitude,
            "message": sos.message,
            "sent_at": datetime.now(tz=timezone.utc).isoformat(),
        }).encode(),
    )

    log.warning(
        "sos_sent",
        sos_id=str(sos_id),
        farm_id=str(sos.farm_id),
        farmer=current_user.get("sub"),
        lat=sos.latitude,
        lon=sos.longitude,
    )

    return {"status": "sos_sent", "sos_id": str(sos_id)}


@router.post(
    "/drill",
    status_code=status.HTTP_201_CREATED,
    summary="Trigger disaster drill (admin only)",
    dependencies=[Depends(require_roles(["flip-admin"]))],
)
async def trigger_drill(
    drill: DrillRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
    nats=Depends(get_nats),
) -> dict:
    import json
    drill_id = uuid.uuid4()

    await session.execute(
        text("""
            INSERT INTO disaster_alerts
                (id, alert_type, severity, title, description,
                 affected_districts, affected_states, evacuation_zones,
                 shelter_locations, source_agency, issued_at,
                 expires_at, is_drill)
            VALUES
                (:id, :alert_type, :severity,
                 'DRILL: ' || :alert_type || ' Alert',
                 'This is a drill. No action required.',
                 :districts, ARRAY['Test State'], ARRAY[]::text[],
                 '[]'::jsonb, 'FLIP System', now(),
                 now() + interval '1 hour', true)
        """),
        {
            "id": str(drill_id),
            "alert_type": drill.alert_type,
            "severity": drill.severity,
            "districts": drill.affected_districts,
        },
    )
    await session.commit()

    await nats.publish(
        subject="disaster.alert",
        payload=json.dumps({
            "alert_id": str(drill_id),
            "is_drill": True,
            "alert_type": drill.alert_type,
            "severity": drill.severity,
            "issued_at": datetime.now(tz=timezone.utc).isoformat(),
        }).encode(),
    )

    return {"status": "drill_started", "alert_id": str(drill_id), "is_drill": True}
