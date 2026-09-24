"""
FLIP Core API — Auth Router Endpoint Module
Exposes auth_router for /api/v1/auth/*
"""

from flip_api.auth.router import router as auth_router

__all__ = ["auth_router"]
