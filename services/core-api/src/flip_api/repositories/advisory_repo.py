"""
FLIP Core API — AdvisoryRepository
Advisory CRUD + conformal-set action tracking + template management.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text

from .base import BaseRepository

logger = structlog.get_logger(__name__)


class AdvisoryRepository(BaseRepository):
    """Advisories, templates, farmer actions, and action verifications."""

    # ------------------------------------------------------------------
    # Advisory Templates (managed by agronomists / platform_admin)
    # ------------------------------------------------------------------

    async def list_templates(
        self, crop_variety: str | None = None
    ) -> list[dict[str, Any]]:
        if crop_variety:
            stmt = text("""
                SELECT id, crop_variety, condition_type, template_json, created_at
                FROM advisory_templates
                WHERE crop_variety = :cv
                ORDER BY condition_type
            """)
            result = await self.session.execute(stmt, {"cv": crop_variety})
        else:
            stmt = text("""
                SELECT id, crop_variety, condition_type, template_json, created_at
                FROM advisory_templates
                ORDER BY crop_variety, condition_type
            """)
            result = await self.session.execute(stmt)
        return [dict(r._mapping) for r in result]

    async def upsert_template(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Insert or update advisory template (crop_variety, condition_type unique)."""
        stmt = text("""
            INSERT INTO advisory_templates
                (crop_variety, condition_type, template_json)
            VALUES
                (:crop_variety, :condition_type, :template_json::jsonb)
            ON CONFLICT (crop_variety, condition_type)
            DO UPDATE SET
                template_json = EXCLUDED.template_json,
                created_at    = now()
            RETURNING id, crop_variety, condition_type, created_at
        """)
        result = await self.session.execute(stmt, payload)
        return dict(result.one()._mapping)

    # ------------------------------------------------------------------
    # Advisories
    # ------------------------------------------------------------------

    async def create_advisory(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Insert a new advisory.
        payload keys: farm_id, field_id?, agronomist_id?,
                      advisory_type, content_json, severity, issued_at
        """
        stmt = text("""
            INSERT INTO advisories
                (farm_id, field_id, agronomist_id,
                 advisory_type, content_json, severity, issued_at)
            VALUES
                (:farm_id, :field_id, :agronomist_id,
                 :advisory_type, :content_json::jsonb, :severity, :issued_at)
            RETURNING id, farm_id, advisory_type, severity, issued_at
        """)
        result = await self.session.execute(stmt, payload)
        row = result.one()
        logger.info(
            "advisory_created",
            advisory_id=str(row.id),
            farm_id=str(row.farm_id),
        )
        return dict(row._mapping)

    async def get_advisory(self, advisory_id: UUID) -> dict[str, Any] | None:
        stmt = text("""
            SELECT id, farm_id, field_id, agronomist_id,
                   advisory_type, content_json, severity,
                   issued_at, farmer_read_at
            FROM advisories
            WHERE id = :aid
        """)
        result = await self.session.execute(stmt, {"aid": str(advisory_id)})
        row = result.one_or_none()
        return dict(row._mapping) if row else None

    async def list_advisories(
        self,
        farm_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT id, advisory_type, severity, issued_at,
                   farmer_read_at, content_json
            FROM advisories
            WHERE farm_id = :fid
            ORDER BY issued_at DESC
            LIMIT :lim OFFSET :off
        """)
        result = await self.session.execute(
            stmt, {"fid": str(farm_id), "lim": limit, "off": offset}
        )
        return [dict(r._mapping) for r in result]

    async def mark_advisory_read(self, advisory_id: UUID) -> bool:
        stmt = text("""
            UPDATE advisories
            SET farmer_read_at = now()
            WHERE id = :aid AND farmer_read_at IS NULL
        """)
        result = await self.session.execute(stmt, {"aid": str(advisory_id)})
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Farmer Actions
    # ------------------------------------------------------------------

    async def create_farmer_action(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Record a farmer's response to an advisory.
        payload keys: farm_id, field_id?, advisory_id?,
                      action_type, action_time, notes, cost_inr
        """
        stmt = text("""
            INSERT INTO farmer_actions
                (farm_id, field_id, advisory_id,
                 action_type, action_time, notes, cost_inr)
            VALUES
                (:farm_id, :field_id, :advisory_id,
                 :action_type, :action_time, :notes, :cost_inr)
            RETURNING id, farm_id, action_type, action_time, cost_inr
        """)
        result = await self.session.execute(stmt, payload)
        row = result.one()
        logger.info("farmer_action_created", action_id=str(row.id))
        return dict(row._mapping)

    # ------------------------------------------------------------------
    # Action Verifications
    # ------------------------------------------------------------------

    async def add_verification(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Verify a farmer action (sensor/image/expert confirmation).
        payload keys: farmer_action_id, verified_by?, method, outcome, notes
        """
        stmt = text("""
            INSERT INTO action_verifications
                (farmer_action_id, verified_by, method, outcome, notes)
            VALUES
                (:farmer_action_id, :verified_by, :method, :outcome, :notes)
            RETURNING id, farmer_action_id, method, outcome, created_at
        """)
        result = await self.session.execute(stmt, payload)
        row = result.one()
        logger.info(
            "action_verified",
            verification_id=str(row.id),
            outcome=row.outcome,
        )
        return dict(row._mapping)

    async def list_verifications(
        self, farmer_action_id: UUID
    ) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT id, verified_by, method, outcome, notes, created_at
            FROM action_verifications
            WHERE farmer_action_id = :aid
            ORDER BY created_at DESC
        """)
        result = await self.session.execute(
            stmt, {"aid": str(farmer_action_id)}
        )
        return [dict(r._mapping) for r in result]
