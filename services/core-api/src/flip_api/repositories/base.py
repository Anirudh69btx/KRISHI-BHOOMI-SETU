"""
FLIP Core API — BaseRepository
All repositories inherit from this class.
Provides:
  - self.session: AsyncSession
  - rls_context() async context manager → sets app.current_user_id / org_id / role
    as LOCAL session variables so PostgreSQL RLS policies activate correctly.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class BaseRepository:
    """Base class for all FLIP repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @asynccontextmanager
    async def rls_context(
        self,
        user_id: str | None,
        org_id: str | None,
        role: str | None,
    ) -> AsyncGenerator[None, None]:
        """
        Set PostgreSQL session-local RLS context variables for the duration of
        the async with block.  Uses SET LOCAL so variables are scoped to the
        current transaction only (safe with connection pooling).

        Usage:
            async with repo.rls_context(user_id, org_id, role):
                result = await repo.list_farms()
        """
        if user_id:
            await self.session.execute(
                text("SET LOCAL app.current_user_id = :u"), {"u": str(user_id)}
            )
        if org_id:
            await self.session.execute(
                text("SET LOCAL app.current_org_id = :o"), {"o": str(org_id)}
            )
        if role:
            await self.session.execute(
                text("SET LOCAL app.current_role = :r"), {"r": role}
            )
        logger.debug(
            "rls_context_set", user_id=user_id, org_id=org_id, role=role
        )
        try:
            yield
        finally:
            # RESET is a no-op if connection is returned to pool mid-txn, but
            # defensive cleanup is still good practice.
            await self.session.execute(text("RESET app.current_user_id"))
            await self.session.execute(text("RESET app.current_org_id"))
            await self.session.execute(text("RESET app.current_role"))
