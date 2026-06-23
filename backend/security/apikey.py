"""API-key authentication for external / service-to-service callers.

Keys are configured via the ``API_KEYS`` setting (comma-separated). The
dependency checks the ``X-API-Key`` header. Use this on machine-facing routes in
addition to (or instead of) JWT auth.
"""
from fastapi import Header, HTTPException, status

from core.config import settings


def valid_api_keys() -> set[str]:
    return {k.strip() for k in settings.API_KEYS.split(",") if k.strip()}


async def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    keys = valid_api_keys()
    if not keys or not x_api_key or x_api_key not in keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key
