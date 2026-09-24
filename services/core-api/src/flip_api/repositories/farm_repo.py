"""
FLIP Core API — FarmRepository
Farm, Field, Device CRUD + spatial queries.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert

from .base import BaseRepository

logger = structlog.get_logger(__name__)


class FarmRepository(BaseRepository):
    """Farm, Field, Device CRUD + PostGIS spatial helpers."""

    # ------------------------------------------------------------------
    # Farms
    # ------------------------------------------------------------------

    async def create_farm(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Insert a new farm row.
        payload keys: org_id, farmer_id, name, total_area_hectares,
                      soil_type, irrigation_type, geometry (WKT or GeoJSON str)
        """
        stmt = text("""
            INSERT INTO farms
                (org_id, farmer_id, name, total_area_hectares,
                 soil_type, irrigation_type, geometry)
            VALUES
                (:org_id, :farmer_id, :name, :total_area_hectares,
                 :soil_type, :irrigation_type,
                 ST_GeomFromGeoJSON(:geometry))
            RETURNING id, name, total_area_hectares, soil_type,
                      irrigation_type, created_at
        """)
        result = await self.session.execute(stmt, payload)
        row = result.one()
        logger.info("farm_created", farm_id=str(row.id))
        return dict(row._mapping)

    async def get_farm(self, farm_id: UUID) -> dict[str, Any] | None:
        stmt = text("""
            SELECT id, org_id, farmer_id, name, total_area_hectares,
                   soil_type, irrigation_type, created_at, updated_at,
                   ST_AsGeoJSON(geometry)::json AS geometry
            FROM farms
            WHERE id = :fid
        """)
        result = await self.session.execute(stmt, {"fid": str(farm_id)})
        row = result.one_or_none()
        return dict(row._mapping) if row else None

    async def list_farms_by_org(self, org_id: UUID) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT id, farmer_id, name, total_area_hectares,
                   soil_type, irrigation_type, created_at,
                   ST_AsGeoJSON(geometry)::json AS geometry
            FROM farms
            WHERE org_id = :oid
            ORDER BY created_at DESC
        """)
        result = await self.session.execute(stmt, {"oid": str(org_id)})
        return [dict(r._mapping) for r in result]

    async def list_farms_by_farmer(self, farmer_id: UUID) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT f.id, f.name, f.total_area_hectares, f.soil_type,
                   f.irrigation_type, f.created_at,
                   ff.role, ff.assigned_at,
                   ST_AsGeoJSON(f.geometry)::json AS geometry
            FROM farms f
            JOIN farmer_farms ff ON ff.farm_id = f.id
            WHERE ff.farmer_id = :uid
            ORDER BY ff.assigned_at DESC
        """)
        result = await self.session.execute(stmt, {"uid": str(farmer_id)})
        return [dict(r._mapping) for r in result]

    async def farms_within_radius(
        self, lat: float, lon: float, radius_m: float
    ) -> list[dict[str, Any]]:
        """PostGIS spatial query — farms within radius_m metres of a point."""
        stmt = text("""
            SELECT id, name, total_area_hectares, soil_type,
                   ST_AsGeoJSON(geometry)::json AS geometry,
                   ST_Distance(
                       geography(geometry),
                       ST_MakePoint(:lon, :lat)::geography
                   ) AS distance_m
            FROM farms
            WHERE ST_DWithin(
                geography(geometry),
                ST_MakePoint(:lon, :lat)::geography,
                :radius
            )
            ORDER BY distance_m
        """)
        result = await self.session.execute(
            stmt, {"lat": lat, "lon": lon, "radius": radius_m}
        )
        return [dict(r._mapping) for r in result]

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    async def create_field(self, payload: dict[str, Any]) -> dict[str, Any]:
        stmt = text("""
            INSERT INTO fields
                (farm_id, name, area_hectares, crop_type, geometry)
            VALUES
                (:farm_id, :name, :area_hectares, :crop_type,
                 ST_GeomFromGeoJSON(:geometry))
            RETURNING id, farm_id, name, area_hectares, crop_type, created_at
        """)
        result = await self.session.execute(stmt, payload)
        row = result.one()
        return dict(row._mapping)

    async def list_fields(self, farm_id: UUID) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT id, name, area_hectares, crop_type, created_at,
                   ST_AsGeoJSON(geometry)::json AS geometry
            FROM fields
            WHERE farm_id = :fid
            ORDER BY created_at
        """)
        result = await self.session.execute(stmt, {"fid": str(farm_id)})
        return [dict(r._mapping) for r in result]

    # ------------------------------------------------------------------
    # Devices
    # ------------------------------------------------------------------

    async def create_device(self, payload: dict[str, Any]) -> dict[str, Any]:
        stmt = text("""
            INSERT INTO devices
                (farm_id, field_id, device_type, serial_number,
                 firmware_version, location, is_active)
            VALUES
                (:farm_id, :field_id, :device_type, :serial_number,
                 :firmware_version,
                 ST_MakePoint(:lon, :lat)::geography,
                 TRUE)
            RETURNING id, farm_id, device_type, serial_number,
                      firmware_version, is_active, created_at
        """)
        result = await self.session.execute(stmt, payload)
        row = result.one()
        return dict(row._mapping)

    async def list_devices(self, farm_id: UUID) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT d.id, d.device_type, d.serial_number,
                   d.firmware_version, d.is_active, d.last_seen_at,
                   d.field_id
            FROM devices d
            WHERE d.farm_id = :fid
            ORDER BY d.device_type, d.serial_number
        """)
        result = await self.session.execute(stmt, {"fid": str(farm_id)})
        return [dict(r._mapping) for r in result]

    async def update_device_heartbeat(self, device_id: UUID) -> None:
        """Touch last_seen_at on device check-in."""
        stmt = text("""
            UPDATE devices
            SET last_seen_at = now()
            WHERE id = :did
        """)
        await self.session.execute(stmt, {"did": str(device_id)})
