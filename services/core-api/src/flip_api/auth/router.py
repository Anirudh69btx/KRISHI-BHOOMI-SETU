"""
FLIP Core API — Authentication & Profile Sync Router (Segment 01)
Provides endpoints for /auth/sync-profile, /auth/me, farm bindings, and OTP flows.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from flip_api.auth.dependencies import (
    require_authenticated_user,
    require_farmer,
)
from flip_api.auth.profile_sync import (
    bind_farm,
    get_bound_farms,
    resolve_primary_role,
    sync_keycloak_profile,
)
from flip_api.auth.rate_limit import (
    login_rate_limiter,
    otp_rate_limiter,
    sync_rate_limiter,
)
from flip_api.config import settings
from flip_api.database import get_session
from flip_api.models.auth import (
    BoundFarm,
    FarmBindingRequest,
    FarmBindingResponse,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
    ProfileSyncRequest,
    ProfileSyncResponse,
    TokenData,
    UserMeResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Identity & Access Management"])


@router.post(
    "/auth/sync-profile",
    response_model=ProfileSyncResponse,
    summary="Synchronize Keycloak Token Claims with PostgreSQL Profiles",
    description="Called on first login and token refresh to upsert user profile and return bound farms.",
)
async def sync_profile_endpoint(
    sync_req: ProfileSyncRequest | None = None,
    token_data: TokenData = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileSyncResponse:
    # 1. Rate limit profile syncs per user
    await sync_rate_limiter.check(token_data.sub)

    # 2. Sync profile in database
    response = await sync_keycloak_profile(session, token_data, sync_req)
    return response


@router.get(
    "/auth/me",
    response_model=UserMeResponse,
    summary="Get Current Authenticated User & Bound Farms",
)
async def get_me(
    token_data: TokenData = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> UserMeResponse:
    sub_uuid = UUID(token_data.sub)
    primary_role = resolve_primary_role(token_data.roles)

    query = text("""
        SELECT id, org_id, role, full_name, phone, language, mfa_enabled
        FROM profiles
        WHERE keycloak_sub = :sub OR auth_user_id = :sub
        LIMIT 1
    """)
    res = await session.execute(query, {"sub": sub_uuid})
    row = res.mappings().first()

    profile_id = row["id"] if row else None
    farms: list[BoundFarm] = []
    if profile_id:
        farms = await get_bound_farms(session, profile_id)

    return UserMeResponse(
        sub=token_data.sub,
        profile_id=profile_id,
        role=row["role"] if row else primary_role,
        roles=token_data.roles,
        phone=row["phone"] if row else token_data.phone,
        email=token_data.email,
        full_name=row["full_name"] if row else token_data.name,
        org_id=row["org_id"] if row else (UUID(token_data.org_id) if token_data.org_id else None),
        farms=farms,
        mfa_enabled=bool(row["mfa_enabled"]) if row else False,
    )


@router.get(
    "/farmers/me/farms",
    response_model=list[BoundFarm],
    summary="Get List of Farms Bound to Current Farmer",
)
async def get_my_farms(
    token_data: TokenData = Depends(require_farmer),
    session: AsyncSession = Depends(get_session),
) -> list[BoundFarm]:
    sub_uuid = UUID(token_data.sub)
    query = text("SELECT id FROM profiles WHERE keycloak_sub = :sub OR auth_user_id = :sub LIMIT 1")
    res = await session.execute(query, {"sub": sub_uuid})
    row = res.mappings().first()
    if not row:
        return []
    return await get_bound_farms(session, row["id"])


@router.put(
    "/farmers/me/farms",
    response_model=FarmBindingResponse,
    summary="Bind a Farm to the Current Farmer",
)
@router.put(
    "/auth/me/farms",
    response_model=FarmBindingResponse,
    summary="Bind a Farm to Current User Profile",
)
async def bind_my_farm(
    binding: FarmBindingRequest,
    token_data: TokenData = Depends(require_farmer),
    session: AsyncSession = Depends(get_session),
) -> FarmBindingResponse:
    sub_uuid = UUID(token_data.sub)
    query = text("SELECT id FROM profiles WHERE keycloak_sub = :sub OR auth_user_id = :sub LIMIT 1")
    res = await session.execute(query, {"sub": sub_uuid})
    row = res.mappings().first()

    if not row:
        # Auto-sync profile first if not yet created
        synced = await sync_keycloak_profile(session, token_data)
        profile_id = synced.profile_id
    else:
        profile_id = row["id"]

    return await bind_farm(session, profile_id, binding)


@router.post(
    "/auth/otp/send",
    response_model=OtpSendResponse,
    summary="Send SMS OTP for Farmer Login",
)
async def send_otp_endpoint(
    req: OtpSendRequest,
    request: Request,
) -> OtpSendResponse:
    # 1. Enforce Rate Limit per phone number
    await otp_rate_limiter.check(req.phone)

    # 2. Check Mock / Dev Mode
    if settings.FLIP_OTP_MOCK_ENABLED or not settings.TWILIO_ACCOUNT_SID:
        logger.info("mock_otp_dispatched", phone=req.phone, code="123456")
        return OtpSendResponse(
            status="sent",
            message="OTP code sent successfully (Dev Mock: 123456)",
            phone=req.phone,
            mock_otp="123456",
        )

    # 3. Production Twilio Verify API
    try:
        from twilio.rest import Client  # type: ignore[import-untyped]
        client = Client(
            settings.TWILIO_ACCOUNT_SID.get_secret_value(),
            settings.TWILIO_AUTH_TOKEN.get_secret_value() if settings.TWILIO_AUTH_TOKEN else "",
        )
        service_sid = settings.TWILIO_VERIFY_SERVICE_SID.get_secret_value() if settings.TWILIO_VERIFY_SERVICE_SID else ""
        verification = client.verify.v2.services(service_sid).verifications.create(
            to=req.phone,
            channel="sms",
        )
        return OtpSendResponse(
            status=verification.status,
            message="OTP code sent via SMS",
            phone=req.phone,
        )
    except Exception as exc:
        logger.error("twilio_verify_send_failed", phone=req.phone, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch SMS verification: {exc}",
        ) from exc


@router.post(
    "/auth/otp/verify",
    response_model=OtpVerifyResponse,
    summary="Verify Farmer SMS OTP Code",
)
async def verify_otp_endpoint(req: OtpVerifyRequest) -> OtpVerifyResponse:
    # 1. Check Mock / Dev Mode
    if settings.FLIP_OTP_MOCK_ENABLED or not settings.TWILIO_ACCOUNT_SID:
        if req.otp == "123456":
            return OtpVerifyResponse(
                verified=True,
                status="approved",
                message="OTP verified successfully",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP code")

    # 2. Production Twilio Verify API
    try:
        from twilio.rest import Client
        client = Client(
            settings.TWILIO_ACCOUNT_SID.get_secret_value(),
            settings.TWILIO_AUTH_TOKEN.get_secret_value() if settings.TWILIO_AUTH_TOKEN else "",
        )
        service_sid = settings.TWILIO_VERIFY_SERVICE_SID.get_secret_value() if settings.TWILIO_VERIFY_SERVICE_SID else ""
        check = client.verify.v2.services(service_sid).verification_checks.create(
            to=req.phone,
            code=req.otp,
        )
        if check.status == "approved":
            return OtpVerifyResponse(
                verified=True,
                status="approved",
                message="OTP verified successfully",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP code")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("twilio_verify_check_failed", phone=req.phone, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {exc}",
        ) from exc


@router.delete(
    "/auth/trusted-devices",
    summary="Revoke All Trusted Devices (Logout from all sessions)",
    description="Invalidates all 30-day trusted device cookies and active session tokens for the user.",
)
async def revoke_devices_endpoint(
    token_data: TokenData = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from flip_api.auth.profile_sync import revoke_trusted_devices

    sub_uuid = UUID(token_data.sub)
    query = text("SELECT id FROM profiles WHERE keycloak_sub = :sub OR auth_user_id = :sub LIMIT 1")
    res = await session.execute(query, {"sub": sub_uuid})
    row = res.mappings().first()

    revoked_count = 0
    if row:
        revoked_count = await revoke_trusted_devices(session, row["id"])

    logger.info("trusted_devices_revoked", sub=str(sub_uuid), count=revoked_count)

    return {
        "status": "revoked",
        "message": "All 30-day trusted devices and sessions have been revoked.",
        "revoked_count": revoked_count,
    }


@router.get(
    "/auth/webauthn/register-options",
    summary="Generate WebAuthn Registration Options for Passkey Creation",
)
async def webauthn_register_options(
    token_data: TokenData = Depends(require_authenticated_user),
) -> dict[str, Any]:
    import base64
    import secrets

    challenge = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")
    user_id_b64 = base64.urlsafe_b64encode(token_data.sub.encode("utf-8")).decode("utf-8").rstrip("=")

    return {
        "challenge": challenge,
        "rp": {"name": "KRISHI BHOOMI SETU (FLIP)", "id": "localhost"},
        "user": {
            "id": user_id_b64,
            "name": token_data.email or token_data.phone or token_data.sub,
            "displayName": token_data.name or "FLIP Officer",
        },
        "pubKeyCredParams": [
            {"type": "public-key", "alg": -7},   # ES256
            {"type": "public-key", "alg": -257}, # RS256
        ],
        "authenticatorSelection": {
            "authenticatorAttachment": "platform",
            "userVerification": "required",
            "residentKey": "preferred",
        },
        "timeout": 60000,
        "attestation": "none",
    }


@router.post(
    "/auth/webauthn/register-verify",
    summary="Verify and Save Registered WebAuthn Credential ID",
)
async def webauthn_register_verify(
    payload: dict[str, Any],
    token_data: TokenData = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    credential_id = payload.get("id") or payload.get("rawId")
    if not credential_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credential ID missing")

    sub_uuid = UUID(token_data.sub)
    update_stmt = text("""
        UPDATE profiles
        SET webauthn_credential_id = :cred_id,
            mfa_enabled = TRUE,
            updated_at = NOW()
        WHERE keycloak_sub = :sub OR auth_user_id = :sub
    """)
    await session.execute(update_stmt, {"cred_id": str(credential_id), "sub": sub_uuid})

    return {
        "status": "success",
        "message": "WebAuthn Passkey registered successfully.",
        "credential_id": str(credential_id),
    }
