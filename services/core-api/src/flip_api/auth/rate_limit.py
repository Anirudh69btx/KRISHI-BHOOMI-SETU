"""
FLIP Core API — Rate Limiting for IAM & OTP Endpoints (Segment 01)
Provides sliding-window rate limiting with Redis and in-memory fallback.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

import structlog
from fastapi import HTTPException, Request, Response, status

from flip_api.config import settings

logger = structlog.get_logger(__name__)

# Fallback In-Memory Storage: key -> list of timestamps
_IN_MEMORY_RATE_LIMITS: dict[str, list[float]] = defaultdict(list)


class RateLimiter:
    """
    Rate limiter for sensitive endpoints (OTP, Login, Profile Sync).
    Keys on IP address or identifier (e.g. phone number).
    """

    def __init__(self, max_requests: int, window_seconds: int, scope: str = "default"):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.scope = scope

    async def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """
        Check if the request is within rate limits.
        Returns: (allowed: bool, retry_after: int)
        """
        key = f"rate_limit:{self.scope}:{identifier}"
        now = time.time()
        window_start = now - self.window_seconds

        # 1. Try Redis if available
        try:
            import redis.asyncio as aioredis  # type: ignore[import-untyped]
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, self.window_seconds)
            results = await pipe.execute()
            await r.aclose()

            current_count = results[1]
            if current_count >= self.max_requests:
                return False, int(self.window_seconds)
            return True, 0
        except Exception:
            # Fallback to In-Memory
            pass

        # In-Memory sliding window
        timestamps = _IN_MEMORY_RATE_LIMITS[key]
        _IN_MEMORY_RATE_LIMITS[key] = [t for t in timestamps if t > window_start]
        if len(_IN_MEMORY_RATE_LIMITS[key]) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - _IN_MEMORY_RATE_LIMITS[key][0]))
            return False, max(1, retry_after)

        _IN_MEMORY_RATE_LIMITS[key].append(now)
        return True, 0

    async def check(self, identifier: str) -> None:
        """Enforce rate limit or raise HTTP 429 Too Many Requests."""
        allowed, retry_after = await self.is_allowed(identifier)
        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                scope=self.scope,
                identifier=identifier,
                retry_after=retry_after,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {self.scope}. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )


# Pre-configured rate limiters
otp_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_OTP_PER_HOUR,
    window_seconds=3600,
    scope="otp",
)

login_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_LOGIN_PER_MIN,
    window_seconds=60,
    scope="login",
)

sync_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_SYNC_PER_MIN,
    window_seconds=60,
    scope="profile_sync",
)
