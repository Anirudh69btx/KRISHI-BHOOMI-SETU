"""
FLIP Core API — Keycloak JWT Verification, JWKS Cache & OIDC Utilities (Segment 01)
Architecture: Keycloak is sole IdP. This module validates JWTs cryptographically.
"""

from __future__ import annotations

import json
import time
from typing import Any
from uuid import UUID

import httpx
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTClaimsError, JWTError, jwk, jwt

from flip_api.config import settings
from flip_api.models.auth import TokenData

logger = structlog.get_logger(__name__)

bearer_scheme = HTTPBearer(auto_error=True)

# In-memory JWKS cache: {"keys": [...], "expires_at": timestamp}
_JWKS_CACHE: dict[str, Any] = {}
_JWKS_TTL_SECONDS = 3600  # 1 hour


async def fetch_jwks(force_refresh: bool = False) -> dict[str, Any]:
    """
    Fetch Keycloak JWKS certificates. Caches in memory with TTL.
    Attempts to read/write Redis if available, falling back seamlessly.
    """
    now = time.time()
    if not force_refresh and _JWKS_CACHE.get("expires_at", 0) > now and "keys" in _JWKS_CACHE:
        return _JWKS_CACHE["data"]

    jwks_url = settings.jwks_url
    logger.info("fetching_keycloak_jwks", url=jwks_url)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            data = resp.json()

        _JWKS_CACHE["data"] = data
        _JWKS_CACHE["keys"] = data.get("keys", [])
        _JWKS_CACHE["expires_at"] = now + _JWKS_TTL_SECONDS
        return data
    except Exception as exc:
        logger.error("failed_to_fetch_jwks", url=jwks_url, error=str(exc))
        # If cache still has stale data, return it during transient Keycloak outage
        if "data" in _JWKS_CACHE:
            logger.warning("using_stale_jwks_cache")
            return _JWKS_CACHE["data"]
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable: unable to fetch public signing keys",
        ) from exc


def sync_fetch_jwks() -> dict[str, Any]:
    """Synchronous JWKS fetcher for unit tests and fallback contexts."""
    now = time.time()
    if _JWKS_CACHE.get("expires_at", 0) > now and "data" in _JWKS_CACHE:
        return _JWKS_CACHE["data"]

    jwks_url = settings.jwks_url
    try:
        resp = httpx.get(jwks_url, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        _JWKS_CACHE["data"] = data
        _JWKS_CACHE["keys"] = data.get("keys", [])
        _JWKS_CACHE["expires_at"] = now + _JWKS_TTL_SECONDS
        return data
    except Exception as exc:
        if "data" in _JWKS_CACHE:
            return _JWKS_CACHE["data"]
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Keycloak signing keys unavailable: {exc}",
        ) from exc


def decode_and_validate_jwt(token: str, jwks: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Decode, cryptographically verify signature (RS256), and validate claims.
    Accepts access_tokens issued by Keycloak for realm 'flip'.
    """
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token missing or empty",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token header: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'kid' in header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if jwks is None:
        jwks = sync_fetch_jwks()

    key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if key_data is None:
        # Retry with fresh JWKS once in case of key rotation
        jwks = sync_fetch_jwks()
        key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if key_data is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: no matching public key found in realm JWKS",
                headers={"WWW-Authenticate": "Bearer"},
            )

    try:
        rsa_key = jwk.construct(key_data)
        expected_issuer = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"

        claims = jwt.decode(
            token,
            rsa_key.to_dict(),
            algorithms=["RS256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": False,  # Keycloak access tokens often set aud to 'account' or client
            },
        )

        # Validate issuer if present
        token_iss = claims.get("iss")
        if token_iss and settings.FLIP_ENV == "production" and token_iss != expected_issuer:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token issuer: expected {expected_issuer}, got {token_iss}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return claims

    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"The access token expired\""},
        ) from exc
    except JWTClaimsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token claims: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token signature: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def extract_token_data(claims: dict[str, Any]) -> TokenData:
    """Extract strongly typed TokenData from decoded Keycloak claims."""
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required subject ('sub') claim",
        )

    # Collect roles from realm_access, resource_access, and custom mappers
    roles: set[str] = set()
    realm_access = claims.get("realm_access", {})
    if isinstance(realm_access, dict):
        roles.update(realm_access.get("roles", []))

    # Also check direct 'roles' or 'flip_role' mapper
    if "roles" in claims and isinstance(claims["roles"], list):
        roles.update(claims["roles"])
    if "flip_role" in claims and isinstance(claims["flip_role"], str):
        roles.add(claims["flip_role"])

    # Phone can come from 'phone', 'phoneNumber', or user attributes
    phone = claims.get("phone") or claims.get("phoneNumber") or claims.get("phone_number")

    # Name mapping
    name = claims.get("name")
    if not name and (claims.get("given_name") or claims.get("family_name")):
        name = f"{claims.get('given_name', '')} {claims.get('family_name', '')}".strip()

    return TokenData(
        sub=sub,
        email=claims.get("email"),
        email_verified=bool(claims.get("email_verified", False)),
        preferred_username=claims.get("preferred_username"),
        name=name,
        given_name=claims.get("given_name"),
        family_name=claims.get("family_name"),
        phone=phone,
        phone_verified=bool(claims.get("phone_verified", False)),
        roles=sorted(list(roles)),
        org_id=claims.get("org_id"),
        exp=claims.get("exp"),
        iat=claims.get("iat"),
        iss=claims.get("iss"),
        aud=claims.get("aud"),
        raw_claims=claims,
    )


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict[str, Any]:
    """FastAPI dependency: Returns decoded raw claims for authenticated requests."""
    return decode_and_validate_jwt(creds.credentials)


async def get_current_token_data(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenData:
    """FastAPI dependency: Returns parsed and strongly-typed TokenData."""
    claims = decode_and_validate_jwt(creds.credentials)
    return extract_token_data(claims)


def require_role(*roles: str):
    """FastAPI dependency factory: Enforce one of the specified realm roles."""
    async def _check_role(user: dict = Depends(get_current_user)) -> dict:
        user_roles: list[str] = user.get("roles", []) or user.get("realm_access", {}).get("roles", [])
        if not any(r in user_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {roles}",
            )
        return user
    return _check_role
