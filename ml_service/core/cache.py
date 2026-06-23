"""Redis-backed prediction cache + a fixed-window rate limiter.

Both degrade gracefully: if Redis is unavailable, caching becomes a no-op and
the rate limiter fails open, so predictions still serve.
"""
import json
import time

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status

from config import settings
from core.security import require_auth

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
    return _client


async def cache_get(key: str) -> dict | None:
    try:
        raw = await get_redis().get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def cache_set(key: str, value: dict, ttl: int | None = None) -> None:
    try:
        await get_redis().set(
            key, json.dumps(value), ex=ttl or settings.PREDICTION_CACHE_TTL
        )
    except Exception:
        pass


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


class RateLimiter:
    """Per-principal fixed-window limiter. Returns the principal for reuse."""

    def __init__(self, per_minute: int | None = None) -> None:
        self.limit = per_minute or settings.RATE_LIMIT_PER_MIN

    async def __call__(self, principal: dict = Depends(require_auth)) -> dict:
        window = int(time.time() // 60)
        key = f"rl:{principal.get('sub', 'anon')}:{window}"
        try:
            redis = get_redis()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 60)
            if count > self.limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                )
        except HTTPException:
            raise
        except Exception:
            pass  # fail open if Redis is down
        return principal


rate_limited = RateLimiter()
