"""
FLIP Core API — Keycloak Profile Synchronizer, Farm Binding & NATS Event Sourcing (Segment 01)
Syncs Keycloak JWT claims into PostgreSQL profiles table, manages farmer_farms bindings,
tracks trusted device fingerprints, and emits CloudEvents to NATS JetStream.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import structlog
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from flip_api.models.auth import (
    BoundFarm,
    FarmBindingRequest,
    FarmBindingResponse,
    ProfileSyncRequest,
    ProfileSyncResponse,
    TokenData,
)

logger = structlog.get_logger(__name__)

# Preferred precedence for mapping realm roles to single profile role
ROLE_PRECEDENCE = [
    "platform_admin",
    "fpo_admin",
    "agronomist",
    "gov_officer",
    "buyer",
    "logistics",
    "farmer",
    "fpo_member",
]


def resolve_primary_role(roles: list[str]) -> str:
    """Resolve the highest-privilege role from Keycloak realm roles."""
    for candidate in ROLE_PRECEDENCE:
        if candidate in roles:
            return candidate
    return "farmer"  # Default fallback for smallholder farmers


async def emit_profile_synced_cloudevent(
    profile_id: UUID,
    keycloak_sub: UUID,
    role: str,
    farm_ids: list[UUID],
    synced_at: datetime,
) -> None:
    """
    Publish CloudEvents v1.0 flip.profile.synced.v1 event to NATS JetStream.
    Target subject: farm.{farm_id}.profile.synced
    """
    try:
        from flip_api import main

        if main.nats_client and main.nats_client._js:
            event = {
                "specversion": "1.0",
                "type": "flip.profile.synced.v1",
                "source": "/services/core-api",
                "id": str(uuid4()),
                "time": synced_at.isoformat(),
                "datacontenttype": "application/json",
                "data": {
                    "profile_id": str(profile_id),
                    "keycloak_sub": str(keycloak_sub),
                    "role": role,
                    "farm_ids": [str(fid) for fid in farm_ids],
                    "synced_at": synced_at.isoformat(),
                },
            }
            targets = farm_ids if farm_ids else [UUID("00000000-0000-0000-0000-000000000000")]
            for fid in targets:
                await main.nats_client.publish(f"farm.{fid}.profile.synced", event)
            logger.info("emitted_profile_synced_event", profile_id=str(profile_id), targets=len(targets))
    except Exception as exc:
        logger.warning("nats_profile_synced_event_failed", error=str(exc))


async def sync_keycloak_profile(
    session: AsyncSession,
    token_data: TokenData,
    sync_req: ProfileSyncRequest | None = None,
) -> ProfileSyncResponse:
    """
    Idempotently upsert Keycloak user into PostgreSQL 'profiles' table.
    Updates last_synced_at, phone, full_name, role, device_fingerprint, and emits CloudEvent.
    """
    sub_uuid = UUID(token_data.sub)
    primary_role = resolve_primary_role(token_data.roles)
    now = datetime.now(timezone.utc)

    full_name = (sync_req and sync_req.full_name) or token_data.name or "FLIP Farmer"
    phone = (sync_req and sync_req.phone) or token_data.phone
    language = (sync_req and sync_req.language) or "hi"
    preferred_channels = (sync_req and sync_req.preferred_channels) or ["PUSH"]
    device_hash = sync_req.device_fingerprint_hash if sync_req else None
    webauthn_id = sync_req.webauthn_credential_id if sync_req else None

    # 1. Lookup existing profile by keycloak_sub OR auth_user_id OR phone
    query = text("""
        SELECT id, keycloak_sub, org_id, role, full_name, phone, language,
               preferred_channels, mfa_enabled, webauthn_credential_id,
               last_trusted_login_at, is_active, created_at, last_synced_at
        FROM profiles
        WHERE keycloak_sub = :sub
           OR auth_user_id = :sub
           OR (phone IS NOT NULL AND phone = :phone AND :phone != '')
        LIMIT 1
    """)
    result = await session.execute(query, {"sub": sub_uuid, "phone": phone or ""})
    row = result.mappings().first()

    profile_id: UUID
    mfa_enabled = bool(token_data.raw_claims.get("mfa_enabled", False)) or bool(webauthn_id)

    if row:
        profile_id = row["id"]
        # Update existing profile
        update_stmt = text("""
            UPDATE profiles
            SET keycloak_sub = :sub,
                auth_user_id = COALESCE(auth_user_id, :sub),
                role = :role,
                full_name = COALESCE(:full_name, full_name),
                phone = COALESCE(:phone, phone),
                language = COALESCE(:language, language),
                preferred_channels = COALESCE(:channels, preferred_channels),
                mfa_enabled = COALESCE(:mfa, mfa_enabled),
                device_fingerprint_hash = COALESCE(:device_hash, device_fingerprint_hash),
                webauthn_credential_id = COALESCE(:webauthn_id, webauthn_credential_id),
                last_trusted_login_at = CASE WHEN :device_hash IS NOT NULL THEN :synced_at ELSE last_trusted_login_at END,
                last_synced_at = :synced_at,
                last_login_at = :synced_at,
                updated_at = :synced_at
            WHERE id = :profile_id
            RETURNING id, role, full_name, phone, language, preferred_channels, mfa_enabled,
                      webauthn_credential_id, last_trusted_login_at, last_synced_at
        """)
        up_res = await session.execute(
            update_stmt,
            {
                "sub": sub_uuid,
                "role": primary_role,
                "full_name": full_name,
                "phone": phone,
                "language": language,
                "channels": preferred_channels,
                "mfa": mfa_enabled,
                "device_hash": device_hash,
                "webauthn_id": webauthn_id,
                "synced_at": now,
                "profile_id": profile_id,
            },
        )
        updated_row = up_res.mappings().first()
    else:
        # Insert new profile
        insert_stmt = text("""
            INSERT INTO profiles (
                id, keycloak_sub, auth_user_id, role, full_name, phone,
                language, preferred_channels, mfa_enabled, device_fingerprint_hash,
                webauthn_credential_id, last_trusted_login_at, is_active,
                last_synced_at, last_login_at, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :sub, :sub, :role, :full_name, :phone,
                :language, :channels, :mfa, :device_hash,
                :webauthn_id, CASE WHEN :device_hash IS NOT NULL THEN :synced_at ELSE NULL END, true,
                :synced_at, :synced_at, :synced_at, :synced_at
            )
            RETURNING id, role, full_name, phone, language, preferred_channels, mfa_enabled,
                      webauthn_credential_id, last_trusted_login_at, last_synced_at
        """)
        ins_res = await session.execute(
            insert_stmt,
            {
                "sub": sub_uuid,
                "role": primary_role,
                "full_name": full_name,
                "phone": phone,
                "language": language,
                "channels": preferred_channels,
                "mfa": mfa_enabled,
                "device_hash": device_hash,
                "webauthn_id": webauthn_id,
                "synced_at": now,
            },
        )
        updated_row = ins_res.mappings().first()
        profile_id = updated_row["id"]
        logger.info("new_profile_created", profile_id=str(profile_id), sub=str(sub_uuid), role=primary_role)

    # 2. Fetch Bound Farms
    farms = await get_bound_farms(session, profile_id)
    farm_ids = [f.farm_id for f in farms]

    # 3. Emit NATS JetStream Event Sourcing CloudEvent
    await emit_profile_synced_cloudevent(
        profile_id=profile_id,
        keycloak_sub=sub_uuid,
        role=updated_row["role"],
        farm_ids=farm_ids,
        synced_at=now,
    )

    return ProfileSyncResponse(
        profile_id=profile_id,
        keycloak_sub=sub_uuid,
        role=updated_row["role"],
        full_name=updated_row["full_name"],
        phone=updated_row["phone"],
        email=token_data.email,
        language=updated_row["language"],
        preferred_channels=list(updated_row["preferred_channels"] or []),
        mfa_enabled=bool(updated_row["mfa_enabled"]),
        webauthn_credential_id=updated_row["webauthn_credential_id"],
        last_trusted_login_at=updated_row["last_trusted_login_at"],
        last_synced_at=updated_row["last_synced_at"],
        farms=farms,
        permissions=token_data.roles,
    )


async def get_bound_farms(session: AsyncSession, profile_id: UUID) -> list[BoundFarm]:
    """Retrieve all farms bound to the given profile via farmer_farms or farms.farmer_id."""
    query = text("""
        SELECT DISTINCT f.id AS farm_id, f.name,
               COALESCE(ff.role, 'OWNER') AS role,
               f.area_hectares,
               COALESCE(ff.assigned_at, f.created_at) AS assigned_at
        FROM farms f
        LEFT JOIN farmer_farms ff ON f.id = ff.farm_id AND ff.farmer_id = :profile_id
        WHERE ff.farmer_id = :profile_id OR f.farmer_id = :profile_id
        ORDER BY assigned_at DESC
    """)
    result = await session.execute(query, {"profile_id": profile_id})
    farms: list[BoundFarm] = []
    for row in result.mappings().all():
        farms.append(
            BoundFarm(
                farm_id=row["farm_id"],
                name=row["name"],
                role=row["role"],
                area_hectares=float(row["area_hectares"]) if row["area_hectares"] is not None else None,
                assigned_at=row["assigned_at"],
            )
        )
    return farms


async def bind_farm(
    session: AsyncSession,
    profile_id: UUID,
    binding: FarmBindingRequest,
) -> FarmBindingResponse:
    """Bind a farmer to a specific farm."""
    farm_check = text("SELECT id, name FROM farms WHERE id = :farm_id")
    res = await session.execute(farm_check, {"farm_id": binding.farm_id})
    if not res.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    upsert_stmt = text("""
        INSERT INTO farmer_farms (farmer_id, farm_id, role, assigned_at)
        VALUES (:farmer_id, :farm_id, :role, NOW())
        ON CONFLICT (farmer_id, farm_id)
        DO UPDATE SET role = EXCLUDED.role, assigned_at = NOW()
        RETURNING assigned_at
    """)
    res = await session.execute(
        upsert_stmt,
        {
            "farmer_id": profile_id,
            "farm_id": binding.farm_id,
            "role": binding.role,
        },
    )
    assigned_at = res.scalar_one()

    logger.info("farm_bound", farmer_id=str(profile_id), farm_id=str(binding.farm_id), role=binding.role)

    return FarmBindingResponse(
        farmer_id=profile_id,
        farm_id=binding.farm_id,
        role=binding.role,
        assigned_at=assigned_at,
        message="Farm successfully bound to farmer",
    )


async def revoke_trusted_devices(session: AsyncSession, profile_id: UUID) -> int:
    """Revoke all 30-day trusted devices for the given profile."""
    stmt = text("""
        UPDATE trusted_devices
        SET is_active = FALSE
        WHERE profile_id = :profile_id AND is_active = TRUE
    """)
    res = await session.execute(stmt, {"profile_id": profile_id})
    return res.rowcount
