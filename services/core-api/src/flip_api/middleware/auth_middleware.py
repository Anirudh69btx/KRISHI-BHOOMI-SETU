"""
FLIP Core API — Auth Middleware (Segment 01)
ASGI HTTP middleware to validate Bearer tokens and attach identity context to request.state.
"""

from __future__ import annotations

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from flip_api.auth.keycloak import decode_and_validate_jwt, extract_token_data
from flip_api.auth.profile_sync import resolve_primary_role

logger = structlog.get_logger(__name__)

# Public paths that do not require mandatory JWT authentication
PUBLIC_PREFIXES = (
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/otp/send",
    "/api/v1/auth/otp/verify",
)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Inspects Authorization header. If present, decodes JWT and populates request.state:
    - request.state.user: dict (raw claims)
    - request.state.token_data: TokenData
    - request.state.current_user_id: str (UUID sub)
    - request.state.current_role: str (primary role)
    - request.state.rls_context: dict with keys user_id, org_id, role
      → passed to BaseRepository.rls_context() or set_rls_context()
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        auth_header = request.headers.get("Authorization")

        request.state.user = None
        request.state.token_data = None
        request.state.current_user_id = None
        request.state.current_role = None
        request.state.rls_context = {"user_id": None, "org_id": None, "role": None}

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:
                claims = decode_and_validate_jwt(token)
                token_data = extract_token_data(claims)
                primary_role = resolve_primary_role(token_data.roles)

                request.state.user = claims
                request.state.token_data = token_data
                request.state.current_user_id = token_data.sub
                request.state.current_role = primary_role

                # RLS context — consumed by repository layer
                request.state.rls_context = {
                    "user_id": token_data.sub,
                    "org_id": token_data.org_id,
                    "role": primary_role,
                }

            except Exception as exc:
                # If path is not public, let route-level dependency raise or log
                path = request.url.path
                if not any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
                    logger.debug("auth_middleware_token_invalid", path=path, error=str(exc))

        response = await call_next(request)
        return response
