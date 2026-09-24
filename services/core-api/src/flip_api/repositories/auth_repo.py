"""
FLIP Core API — AuthRepository
Profile sync from Keycloak, farmer_farms bindings, trusted device management.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text

from .base import BaseRepository

logger = structlog.get_logger(__name__)


class AuthRepository(BaseRepository):
    """
    Identity & Access data access:
      - Profile upsert on JWT login (Keycloak sub linkage)
      - Farmer → Farm role bindings
      - Trusted device HMAC registry
    """

    # ------------------------------------------------------------------
    # Profiles
    # ------------------------------------------------------------------

    async def upsert_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Upsert profile on every authenticated request (Keycloak sync).
        Uses keycloak_sub as the conflict target so a user is created
        once and updated on subsequent logins.

        payload keys: keycloak_sub, email, full_name, phone,
                      org_id, role, language
        """
        stmt = text("""
            INSERT INTO profiles
                (keycloak_sub, email, full_name, phone,
                 org_id, role, language, last_synced_at)
            VALUES
                (:keycloak_sub, :email, :full_name, :phone,
                 :org_id, :role, :language, now())
            ON CONFLICT (keycloak_sub)
            DO UPDATE SET
                email          = EXCLUDED.email,
                full_name      = EXCLUDED.full_name,
                phone          = EXCLUDED.phone,
                org_id         = COALESCE(EXCLUDED.org_id, profiles.org_id),
                role           = EXCLUDED.role,
                language       = COALESCE(EXCLUDED.language, profiles.language),
                last_synced_at = now()
            RETURNING id, keycloak_sub, role, email, full_name,
                      phone, org_id, language, mfa_enabled,
                      last_synced_at, last_trusted_login_at
        """)
        result = await self.session.execute(stmt, payload)
        row = result.one()
        logger.info(
            "profile_upserted",
            profile_id=str(row.id),
            keycloak_sub=str(row.keycloak_sub),
        )
        return dict(row._mapping)

    async def get_profile_by_keycloak_sub(
        self, keycloak_sub: str
    ) -> dict[str, Any] | None:
        stmt = text("""
            SELECT id, keycloak_sub, email, full_name, phone,
                   org_id, role, language, mfa_enabled,
                   last_synced_at, last_trusted_login_at,
                   preferred_channels
            FROM profiles
            WHERE keycloak_sub = :ks
        """)
        result = await self.session.execute(
            stmt, {"ks": str(keycloak_sub)}
        )
        row = result.one_or_none()
        return dict(row._mapping) if row else None

    async def get_profile(self, profile_id: UUID) -> dict[str, Any] | None:
        stmt = text("""
            SELECT id, keycloak_sub, email, full_name, phone,
                   org_id, role, language, mfa_enabled,
                   last_synced_at, last_trusted_login_at,
                   preferred_channels
            FROM profiles
            WHERE id = :pid
        """)
        result = await self.session.execute(stmt, {"pid": str(profile_id)})
        row = result.one_or_none()
        return dict(row._mapping) if row else None

    async def update_profile_prefs(
        self, profile_id: UUID, payload: dict[str, Any]
    ) -> None:
        """Partial update for user-controlled preferences."""
        stmt = text("""
            UPDATE profiles
            SET language            = COALESCE(:language, language),
                preferred_channels  = COALESCE(:preferred_channels, preferred_channels),
                mfa_enabled         = COALESCE(:mfa_enabled, mfa_enabled)
            WHERE id = :pid
        """)
        await self.session.execute(
            stmt,
            {
                "pid": str(profile_id),
                "language": payload.get("language"),
                "preferred_channels": payload.get("preferred_channels"),
                "mfa_enabled": payload.get("mfa_enabled"),
            },
        )

    # ------------------------------------------------------------------
    # Farmer ↔ Farm Bindings
    # ------------------------------------------------------------------

    async def bind_farmer_farm(
        self,
        farmer_id: UUID,
        farm_id: UUID,
        role: str = "OWNER",
    ) -> dict[str, Any]:
        """
        Bind a farmer to a farm with a role.
        Uses ON CONFLICT DO UPDATE to allow role changes.
        """
        stmt = text("""
            INSERT INTO farmer_farms (farmer_id, farm_id, role)
            VALUES (:farmer_id, :farm_id, :role)
            ON CONFLICT (farmer_id, farm_id)
            DO UPDATE SET role = EXCLUDED.role
            RETURNING farmer_id, farm_id, role, assigned_at
        """)
        result = await self.session.execute(
            stmt,
            {
                "farmer_id": str(farmer_id),
                "farm_id": str(farm_id),
                "role": role,
            },
        )
        row = result.one()
        logger.info(
            "farmer_farm_bound",
            farmer_id=str(farmer_id),
            farm_id=str(farm_id),
            role=role,
        )
        return dict(row._mapping)

    async def get_farmer_farms(
        self, farmer_id: UUID
    ) -> list[dict[str, Any]]:
        """Return all farms (with roles) that a farmer is bound to."""
        stmt = text("""
            SELECT f.id AS farm_id, f.name, f.total_area_hectares,
                   ff.role, ff.assigned_at,
                   ST_AsGeoJSON(f.geometry)::json AS geometry
            FROM farmer_farms ff
            JOIN farms f ON f.id = ff.farm_id
            WHERE ff.farmer_id = :uid
            ORDER BY ff.assigned_at DESC
        """)
        result = await self.session.execute(stmt, {"uid": str(farmer_id)})
        return [dict(r._mapping) for r in result]

    # ------------------------------------------------------------------
    # Trusted Devices
    # ------------------------------------------------------------------

    async def register_trusted_device(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Register a trusted device HMAC signature.
        payload keys: farmer_id, device_fingerprint_hash, user_agent,
                      ip_subnet, hmac_signature, expires_at
        """
        stmt = text("""
            INSERT INTO trusted_devices
                (farmer_id, device_fingerprint_hash, user_agent,
                 ip_subnet, hmac_signature, expires_at)
            VALUES
                (:farmer_id, :device_fingerprint_hash, :user_agent,
                 :ip_subnet, :hmac_signature, :expires_at)
            RETURNING id, farmer_id, expires_at, created_at
        """)
        result = await self.session.execute(stmt, payload)
        row = result.one()
        logger.info(
            "trusted_device_registered",
            device_id=str(row.id),
            farmer_id=str(row.farmer_id),
        )
        return dict(row._mapping)

    async def verify_trusted_device(
        self,
        farmer_id: UUID,
        device_fingerprint_hash: str,
        hmac_signature: str,
    ) -> bool:
        """Return True if a valid non-expired trusted device record exists."""
        stmt = text("""
            SELECT count(*) FROM trusted_devices
            WHERE farmer_id              = :fid
              AND device_fingerprint_hash = :fp
              AND hmac_signature          = :sig
              AND expires_at              > now()
        """)
        result = await self.session.execute(
            stmt,
            {
                "fid": str(farmer_id),
                "fp": device_fingerprint_hash,
                "sig": hmac_signature,
            },
        )
        return result.scalar_one() > 0

    async def revoke_trusted_device(self, device_id: UUID) -> None:
        """Immediately expire a trusted device (logout / revoke)."""
        stmt = text("""
            UPDATE trusted_devices
            SET expires_at = now()
            WHERE id = :did
        """)
        await self.session.execute(stmt, {"did": str(device_id)})

    async def list_trusted_devices(
        self, farmer_id: UUID
    ) -> list[dict[str, Any]]:
        """List active trusted devices for a farmer."""
        stmt = text("""
            SELECT id, device_fingerprint_hash, user_agent,
                   ip_subnet, expires_at, created_at
            FROM trusted_devices
            WHERE farmer_id  = :fid
              AND expires_at > now()
            ORDER BY created_at DESC
        """)
        result = await self.session.execute(stmt, {"fid": str(farmer_id)})
        return [dict(r._mapping) for r in result]
