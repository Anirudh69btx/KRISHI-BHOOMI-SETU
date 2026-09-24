"""
FLIP v3.0 — Core API REST Routers
Advisories router: query, acknowledge, and generate AI advisories.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from flip_api.auth.keycloak import get_current_user
from flip_api.database import get_session

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/advisories", tags=["advisories"])


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class AdvisoryResponse(BaseModel):
    id: str
    farm_id: str
    advisory_type: str
    severity: str
    title: str
    title_local: Optional[dict] = None
    body: str
    body_local: Optional[dict] = None
    recommended_actions: Optional[list[str]] = None
    confidence: float
    source: str
    valid_from: str
    valid_until: Optional[str] = None
    acknowledged_at: Optional[str] = None
    created_at: str


class AdvisoryFeedback(BaseModel):
    farm_id: uuid.UUID
    action_taken: str
    notes: Optional[str] = None
    effectiveness_rating: Optional[int] = None  # 1-5


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get(
    "/farms/{farm_id}",
    response_model=list[AdvisoryResponse],
    summary="Get advisories for a farm",
)
async def get_farm_advisories(
    farm_id: uuid.UUID,
    unread_only: bool = Query(False, description="Only return unacknowledged advisories"),
    advisory_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    query = text("""
        SELECT
            id::text, farm_id::text, advisory_type, severity,
            title, title_local, body, body_local,
            recommended_actions, confidence, source,
            valid_from::text, valid_until::text,
            acknowledged_at::text, created_at::text
        FROM advisories
        WHERE farm_id = :farm_id
          AND created_at >= :since
          AND (:unread_only = false OR acknowledged_at IS NULL)
          AND (:advisory_type IS NULL OR advisory_type = :advisory_type)
          AND (:severity IS NULL OR severity = :severity)
        ORDER BY
            CASE severity
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
                ELSE 5
            END,
            created_at DESC
        LIMIT 50
    """)

    result = await session.execute(
        query,
        {
            "farm_id": str(farm_id),
            "since": since,
            "unread_only": unread_only,
            "advisory_type": advisory_type,
            "severity": severity,
        },
    )
    return [dict(r) for r in result.mappings().all()]


@router.post(
    "/{advisory_id}/acknowledge",
    status_code=status.HTTP_200_OK,
    summary="Acknowledge an advisory",
)
async def acknowledge_advisory(
    advisory_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    result = await session.execute(
        text("""
            UPDATE advisories
            SET acknowledged_at = now(),
                acknowledged_by = :user_id
            WHERE id = :id
              AND acknowledged_at IS NULL
            RETURNING id::text, acknowledged_at::text
        """),
        {"id": str(advisory_id), "user_id": current_user.get("sub")},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Advisory not found or already acknowledged",
        )
    await session.commit()
    return dict(row)


@router.post(
    "/{advisory_id}/feedback",
    status_code=status.HTTP_201_CREATED,
    summary="Submit farmer action feedback for an advisory (closes the loop)",
)
async def submit_feedback(
    advisory_id: uuid.UUID,
    feedback: AdvisoryFeedback,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    action_id = uuid.uuid4()

    await session.execute(
        text("""
            INSERT INTO farmer_actions
                (id, farm_id, advisory_id, farmer_id, action_taken, notes,
                 effectiveness_rating, recorded_at)
            VALUES
                (:id, :farm_id, :advisory_id, :farmer_id, :action_taken, :notes,
                 :effectiveness_rating, now())
        """),
        {
            "id": str(action_id),
            "farm_id": str(feedback.farm_id),
            "advisory_id": str(advisory_id),
            "farmer_id": current_user.get("farmer_id"),
            "action_taken": feedback.action_taken,
            "notes": feedback.notes,
            "effectiveness_rating": feedback.effectiveness_rating,
        },
    )
    await session.commit()

    log.info(
        "advisory_feedback_submitted",
        advisory_id=str(advisory_id),
        action_id=str(action_id),
        farmer=current_user.get("sub"),
    )
    return {"status": "recorded", "action_id": str(action_id)}
