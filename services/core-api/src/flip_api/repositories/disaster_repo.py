"""
FLIP Core API — DisasterRepository
Geo-fenced disaster alert queries + multi-channel dispatch tracking.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text

from .base import BaseRepository

logger = structlog.get_logger(__name__)


class DisasterRepository(BaseRepository):
    """Disaster alerts (geo-fenced) + dispatch log management."""

    # ------------------------------------------------------------------
    # Disaster Alerts
    # ------------------------------------------------------------------

    async def create_alert(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Insert a new disaster alert.
        payload keys: alert_type, severity, title, description,
                      issued_by, geometry (GeoJSON string),
                      affected_district, radius_km, issued_at, expires_at
        """
        stmt = text("""
            INSERT INTO disaster_alerts
                (alert_type, severity, title, description,
                 issued_by, geometry, affected_district,
                 radius_km, issued_at, expires_at)
            VALUES
                (:alert_type, :severity, :title, :description,
                 :issued_by, ST_GeomFromGeoJSON(:geometry),
                 :affected_district, :radius_km,
                 :issued_at, :expires_at)
            RETURNING id, alert_type, severity, issued_at, affected_district
        """)
        result = await self.session.execute(stmt, payload)
        row = result.one()
        logger.info(
            "disaster_alert_created",
            alert_id=str(row.id),
            alert_type=row.alert_type,
            severity=row.severity,
        )
        return dict(row._mapping)

    async def get_alert(self, alert_id: UUID) -> dict[str, Any] | None:
        stmt = text("""
            SELECT id, alert_type, severity, title, description,
                   affected_district, radius_km,
                   issued_at, expires_at,
                   ST_AsGeoJSON(geometry)::json AS geometry
            FROM disaster_alerts
            WHERE id = :aid
        """)
        result = await self.session.execute(stmt, {"aid": str(alert_id)})
        row = result.one_or_none()
        return dict(row._mapping) if row else None

    async def get_active_alerts_for_farm(
        self, farm_id: UUID
    ) -> list[dict[str, Any]]:
        """
        Return all active alerts whose geometry intersects the farm boundary.
        Uses PostGIS ST_Intersects for geo-fencing.
        """
        stmt = text("""
            SELECT da.id, da.alert_type, da.severity, da.title,
                   da.affected_district, da.issued_at, da.expires_at
            FROM disaster_alerts da
            JOIN farms f ON ST_Intersects(
                da.geometry,
                f.geometry
            )
            WHERE f.id = :fid
              AND da.expires_at > now()
            ORDER BY da.severity DESC, da.issued_at DESC
        """)
        result = await self.session.execute(stmt, {"fid": str(farm_id)})
        return [dict(r._mapping) for r in result]

    async def list_alerts_by_district(
        self,
        district: str,
        active_only: bool = True,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if active_only:
            stmt = text("""
                SELECT id, alert_type, severity, title,
                       issued_at, expires_at, affected_district
                FROM disaster_alerts
                WHERE affected_district = :dist
                  AND expires_at > now()
                ORDER BY issued_at DESC
                LIMIT :lim
            """)
        else:
            stmt = text("""
                SELECT id, alert_type, severity, title,
                       issued_at, expires_at, affected_district
                FROM disaster_alerts
                WHERE affected_district = :dist
                ORDER BY issued_at DESC
                LIMIT :lim
            """)
        result = await self.session.execute(
            stmt, {"dist": district, "lim": limit}
        )
        return [dict(r._mapping) for r in result]

    # ------------------------------------------------------------------
    # Disaster Dispatches (delivery log per channel)
    # ------------------------------------------------------------------

    async def create_dispatch(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Log a dispatch attempt for a disaster alert.
        payload keys: disaster_alert_id, channel, recipient, status
        """
        stmt = text("""
            INSERT INTO disaster_dispatches
                (disaster_alert_id, channel, recipient, status)
            VALUES
                (:disaster_alert_id, :channel, :recipient, :status)
            RETURNING id, disaster_alert_id, channel, status, sent_at
        """)
        result = await self.session.execute(stmt, payload)
        row = result.one()
        logger.info(
            "disaster_dispatch_created",
            dispatch_id=str(row.id),
            channel=row.channel,
            status=row.status,
        )
        return dict(row._mapping)

    async def update_dispatch_status(
        self,
        dispatch_id: UUID,
        status: str,
        error: str | None = None,
    ) -> None:
        """Mark a dispatch as DELIVERED or FAILED."""
        stmt = text("""
            UPDATE disaster_dispatches
            SET status       = :status,
                delivered_at = CASE WHEN :status = 'DELIVERED' THEN now() END,
                error        = :error
            WHERE id = :did
        """)
        await self.session.execute(
            stmt,
            {"did": str(dispatch_id), "status": status, "error": error},
        )

    async def list_dispatches(
        self, alert_id: UUID
    ) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT id, channel, recipient, status,
                   sent_at, delivered_at, error
            FROM disaster_dispatches
            WHERE disaster_alert_id = :aid
            ORDER BY sent_at DESC
        """)
        result = await self.session.execute(stmt, {"aid": str(alert_id)})
        return [dict(r._mapping) for r in result]

    async def get_dispatch_stats(
        self, alert_id: UUID
    ) -> dict[str, Any]:
        """Aggregate dispatch outcomes for an alert — for monitoring."""
        stmt = text("""
            SELECT
                channel,
                count(*) FILTER (WHERE status = 'DELIVERED') AS delivered,
                count(*) FILTER (WHERE status = 'FAILED')    AS failed,
                count(*) FILTER (WHERE status = 'PENDING')   AS pending,
                count(*)                                     AS total
            FROM disaster_dispatches
            WHERE disaster_alert_id = :aid
            GROUP BY channel
        """)
        result = await self.session.execute(stmt, {"aid": str(alert_id)})
        return {r.channel: dict(r._mapping) for r in result}
