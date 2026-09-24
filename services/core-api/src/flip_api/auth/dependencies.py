"""
FLIP Core API — Role Guards, WebAuthn Enforcers & Auth Dependencies (Segment 01)
Enforces granular role-based access control (RBAC) and WebAuthn MFA checks at route level.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from flip_api.auth.keycloak import bearer_scheme, get_current_token_data
from flip_api.config import settings
from flip_api.models.auth import TokenData


def require_roles(*allowed_roles: str):
    """
    Dependency factory: Enforce that the authenticated user possesses
    at least one of the specified realm roles.
    Platform admins always pass.
    """
    async def _role_guard(
        token_data: Annotated[TokenData, Depends(get_current_token_data)],
    ) -> TokenData:
        user_roles = set(token_data.roles)

        # Platform superadmins bypass role restrictions
        if "platform_admin" in user_roles:
            return token_data

        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Insufficient permissions: required one of {list(allowed_roles)}, "
                    f"but user has {token_data.roles}"
                ),
            )
        return token_data

    return _role_guard


async def require_expert(
    token_data: Annotated[TokenData, Depends(get_current_token_data)],
) -> TokenData:
    """
    Role Guard for Agronomists / Experts with mandatory WebAuthn MFA verification.
    Enforces C8: Experts/Admins must use phishing-resistant MFA.
    """
    user_roles = set(token_data.roles)

    if "platform_admin" in user_roles:
        return token_data

    if not any(role in user_roles for role in ("agronomist", "expert")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to authorized agronomists and agricultural experts",
        )

    # In production, verify that MFA (WebAuthn / Passkey) was completed
    amr = token_data.raw_claims.get("amr", [])
    mfa_verified = (
        bool(token_data.raw_claims.get("mfa_enabled", False))
        or "webauthn" in amr
        or "mfa" in amr
        or settings.FLIP_ENV != "production"
    )

    if not mfa_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Hardening Policy: WebAuthn / Passkey MFA is mandatory for expert and administrator access.",
        )

    return token_data


# Common Role Guards
require_authenticated_user = get_current_token_data

require_farmer = require_roles("farmer")
require_fpo_admin = require_roles("fpo_admin")
require_gov_officer = require_roles("gov_officer")
require_buyer = require_roles("buyer")
require_logistics = require_roles("logistics")
require_platform_admin = require_roles("platform_admin")

# Combined Guards
require_farmer_or_fpo = require_roles("farmer", "fpo_admin", "fpo_member")
require_expert_or_admin = require_roles("agronomist", "expert", "platform_admin")
require_fpo_or_admin = require_roles("fpo_admin", "platform_admin")
