"""
FLIP Core API — TwinRepository
Digital Twin materialized view + twin_events event sourcing.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text

from .base import BaseRepository

logger = structlog.get_logger(__name__)


class TwinRepository(BaseRepository):
    """Digital Twin read model (materialized view) + event sourcing (twin_events)."""

    # ------------------------------------------------------------------
    # Digital Twin — Materialized View (fast read)
    # ------------------------------------------------------------------

    async def get_twin(self, farm_id: UUID) -> dict[str, Any] | None:
        """
        Read the pre-computed farm digital twin snapshot from the
        farm_digital_twin materialized view.
        This is the primary data source for dashboard rendering.
        """
        stmt = text("""
            SELECT *
            FROM farm_digital_twin
            WHERE farm_id = :fid
        """)
        result = await self.session.execute(stmt, {"fid": str(farm_id)})
        row = result.one_or_none()
        return dict(row._mapping) if row else None

    async def list_twins_by_org(
        self, org_id: UUID
    ) -> list[dict[str, Any]]:
        """Return twin snapshots for all farms in an org (dashboard overview)."""
        stmt = text("""
            SELECT fdt.*
            FROM farm_digital_twin fdt
            JOIN farms f ON f.id = fdt.farm_id
            WHERE f.org_id = :oid
            ORDER BY fdt.farm_id
        """)
        result = await self.session.execute(stmt, {"oid": str(org_id)})
        return [dict(r._mapping) for r in result]

    # ------------------------------------------------------------------
    # Twin Events — Event Sourcing (append-only log)
    # ------------------------------------------------------------------

    async def append_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Append a new twin event to the event log.
        payload keys: farm_id, field_id?, event_type, payload (jsonb),
                      occurred_at, source, version
        The NATS bridge trigger on twin_events will forward this to JetStream.
        """
        stmt = text("""
            INSERT INTO twin_events
                (farm_id, field_id, event_type, payload,
                 occurred_at, source, version)
            VALUES
                (:farm_id, :field_id, :event_type, :payload::jsonb,
                 :occurred_at, :source, :version)
            RETURNING id, farm_id, event_type, occurred_at, source
        """)
        result = await self.session.execute(stmt, payload)
        row = result.one()
        logger.info(
            "twin_event_appended",
            event_id=str(row.id),
            farm_id=str(row.farm_id),
            event_type=row.event_type,
        )
        return dict(row._mapping)

    async def get_event_history(
        self,
        farm_id: UUID,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Retrieve ordered event history for a farm.
        Optionally filter by event_type.
        """
        if event_type:
            stmt = text("""
                SELECT id, event_type, payload, occurred_at, source, version
                FROM twin_events
                WHERE farm_id    = :fid
                  AND event_type = :etype
                ORDER BY occurred_at DESC
                LIMIT :lim OFFSET :off
            """)
            params: dict[str, Any] = {
                "fid": str(farm_id),
                "etype": event_type,
                "lim": limit,
                "off": offset,
            }
        else:
            stmt = text("""
                SELECT id, event_type, payload, occurred_at, source, version
                FROM twin_events
                WHERE farm_id = :fid
                ORDER BY occurred_at DESC
                LIMIT :lim OFFSET :off
            """)
            params = {
                "fid": str(farm_id),
                "lim": limit,
                "off": offset,
            }
        result = await self.session.execute(stmt, params)
        return [dict(r._mapping) for r in result]

    async def get_event_count(
        self, farm_id: UUID, event_type: str | None = None
    ) -> int:
        """Total event count — for pagination."""
        if event_type:
            stmt = text("""
                SELECT count(*) FROM twin_events
                WHERE farm_id = :fid AND event_type = :etype
            """)
            result = await self.session.execute(
                stmt, {"fid": str(farm_id), "etype": event_type}
            )
        else:
            stmt = text("""
                SELECT count(*) FROM twin_events WHERE farm_id = :fid
            """)
            result = await self.session.execute(stmt, {"fid": str(farm_id)})
        return result.scalar_one()
