"""Redis-backed API rate limiting.

A fixed-window counter per identity (per-user when a valid JWT is present,
otherwise per-IP) with tier-based limits. Applied as middleware to every
``/api`` request. Fails **open** — if Redis is unavailable the request is
allowed rather than the API going dark.
"""
import logging

from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.config import settings
from core.redis_client import get_redis
from core.security import TOKEN_TYPE_ACCESS, decode_token
from security.rbac import rate_limit_for_role

logger = logging.getLogger(__name__)


async def check_rate_limit(redis, key: str, limit: int, window: int) -> tuple[bool, int, int]:
    """Increment ``key`` within ``window`` seconds. Returns (allowed, count, ttl)."""
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window)
        ttl = window
    else:
        ttl = await redis.ttl(key)
        if ttl < 0:  # key existed without TTL (shouldn't happen) — repair it
            await redis.expire(key, window)
            ttl = window
    return count <= limit, count, ttl


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _identity(request: Request) -> tuple[str, int]:
    """Return (redis_key, limit) for the caller, by tier."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            payload = decode_token(auth[7:], expected_type=TOKEN_TYPE_ACCESS)
            sub = payload.get("sub")
            role = payload.get("role")
            if sub:
                return f"ratelimit:user:{sub}", rate_limit_for_role(role)
        except JWTError:
            pass  # invalid token → treat as anonymous (per-IP)
    ip = _client_ip(request)
    return f"ratelimit:ip:{ip}", settings.RATE_LIMIT_ANON


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-identity request throttling on the ``/api`` surface."""

    async def dispatch(self, request: Request, call_next):
        enabled = getattr(
            request.app.state, "rate_limit_enabled", settings.RATE_LIMIT_ENABLED
        )
        path = request.url.path
        if not enabled or not path.startswith(settings.API_V1_PREFIX):
            return await call_next(request)

        key, limit = _identity(request)
        window = settings.RATE_LIMIT_WINDOW
        try:
            allowed, count, ttl = await check_rate_limit(get_redis(), key, limit, window)
        except Exception:
            return await call_next(request)  # fail-open if Redis is down

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Slow down."},
                headers={
                    "Retry-After": str(ttl),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(ttl),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        response.headers["X-RateLimit-Reset"] = str(ttl)
        return response
