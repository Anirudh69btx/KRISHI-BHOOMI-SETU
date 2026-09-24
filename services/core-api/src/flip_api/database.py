"""
FLIP Core API — Async SQLAlchemy Engine + Session Factory
Supports pgbouncer transaction mode (asyncpg).
"""

from __future__ import annotations

from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from flip_api.config import settings

logger = structlog.get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all FLIP ORM models."""


async def create_engine_and_pool() -> AsyncEngine:
    global _engine, _session_factory  # noqa: PLW0603
    _engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,
        # pgbouncer transaction mode: disable server-side prepared statements
        connect_args={
            "prepared_statement_cache_size": 0,
            "statement_cache_size": 0,
        },
        echo=settings.FLIP_ENV == "local",
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    logger.info(
        "Database engine created",
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
    )
    return _engine


async def close_engine() -> None:
    global _engine  # noqa: PLW0603
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async DB session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call create_engine_and_pool() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# RLS Context Helper
# ---------------------------------------------------------------------------

from sqlalchemy import text  # noqa: E402 (local import to avoid circular)


async def set_rls_context(
    session: AsyncSession,
    user_id: str | None,
    org_id: str | None,
    role: str | None,
) -> None:
    """
    Set PostgreSQL session-local variables that drive RLS policies:
      - app.current_user_id
      - app.current_org_id
      - app.current_role

    Uses SET LOCAL so the variables are scoped to the current transaction
    and automatically reset when the transaction ends — safe with pgbouncer.

    Called by AuthMiddleware immediately after JWT validation so every
    downstream repository query sees the correct RLS context.
    """
    if user_id:
        await session.execute(
            text("SET LOCAL app.current_user_id = :u"), {"u": str(user_id)}
        )
    if org_id:
        await session.execute(
            text("SET LOCAL app.current_org_id = :o"), {"o": str(org_id)}
        )
    if role:
        await session.execute(
            text("SET LOCAL app.current_role = :r"), {"r": role}
        )


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory (for background tasks / scripts)."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized.")
    return _session_factory


# Convenience alias for background tasks that need a standalone session
AsyncSessionLocal = get_session_factory
