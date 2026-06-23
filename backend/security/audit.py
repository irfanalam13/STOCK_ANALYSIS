"""Audit logging: a service to record actions + middleware for API access.

``record_audit`` is the reusable primitive (used by routes and the middleware).
``AuditMiddleware`` automatically logs every mutating ``/api`` request
(POST/PUT/PATCH/DELETE) — covering trades, alert changes, auth, etc.

The middleware resolves its DB session from ``app.state.test_session`` when set
(tests) and otherwise from ``AsyncSessionLocal`` (production), so audit writes
are testable yet never touch the request's own session. All writes are
best-effort: an audit failure must never break the underlying request.
"""
import logging

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.config import settings
from core.database import AsyncSessionLocal
from core.security import TOKEN_TYPE_ACCESS, decode_token
from security.models import AuditLog

logger = logging.getLogger(__name__)

_AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    user_id: int | None = None,
    method: str | None = None,
    path: str | None = None,
    status_code: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    meta: dict | None = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user_id, action=action, method=method, path=path,
        status_code=status_code, ip_address=ip_address,
        user_agent=user_agent, meta=meta,
    )
    db.add(log)
    await db.flush()
    return log


async def list_audit(
    db: AsyncSession,
    user_id: int | None = None,
    action: str | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = await db.execute(stmt.limit(limit))
    return list(rows.scalars().all())


def _user_id_from_request(request: Request) -> int | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            payload = decode_token(auth[7:], expected_type=TOKEN_TYPE_ACCESS)
            return int(payload["sub"])
        except (JWTError, KeyError, ValueError):
            return None
    return None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        path = request.url.path
        if (
            request.method not in _AUDITED_METHODS
            or not path.startswith(settings.API_V1_PREFIX)
        ):
            return response

        factory = getattr(request.app.state, "test_session", None) or AsyncSessionLocal
        fwd = request.headers.get("x-forwarded-for")
        ip = (fwd.split(",")[0].strip() if fwd
              else request.client.host if request.client else None)
        try:
            async with factory() as db:
                await record_audit(
                    db,
                    action=f"{request.method} {path}",
                    user_id=_user_id_from_request(request),
                    method=request.method,
                    path=path,
                    status_code=response.status_code,
                    ip_address=ip,
                    user_agent=request.headers.get("user-agent", "")[:255] or None,
                )
                await db.commit()
        except Exception:  # noqa: BLE001 — audit must never break the request
            logger.debug("audit write failed for %s %s", request.method, path)
        return response
