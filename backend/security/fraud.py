"""Rule-based fraud / abuse detection.

Scans recent audit activity for abnormal patterns and raises ``AccountFlag``
rows for admin review. Deliberately simple and explainable (thresholds), with a
clean seam to add ML-based anomaly scoring later.

Rules:
* **rapid_trading** — more than ``FRAUD_MAX_TRADES`` buy/sell actions within
  ``FRAUD_TRADE_WINDOW`` seconds.
* **request_spike** — more than ``FRAUD_MAX_REQUESTS`` audited API calls within
  ``FRAUD_REQUEST_WINDOW`` seconds.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from security.models import AccountFlag, AuditLog


async def _count_audit(
    db: AsyncSession, user_id: int, since: datetime, path_like: str | None = None
) -> int:
    stmt = (
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.user_id == user_id, AuditLog.timestamp >= since)
    )
    if path_like:
        stmt = stmt.where(AuditLog.path.like(path_like))
    return int((await db.execute(stmt)).scalar_one())


async def _has_unresolved(db: AsyncSession, user_id: int, reason: str) -> bool:
    stmt = select(AccountFlag.id).where(
        AccountFlag.user_id == user_id,
        AccountFlag.reason == reason,
        AccountFlag.resolved.is_(False),
    )
    return (await db.execute(stmt)).first() is not None


async def _raise_flag(
    db: AsyncSession, user_id: int, reason: str, severity: str, details: dict
) -> AccountFlag | None:
    # Don't pile up duplicate open flags for the same reason.
    if await _has_unresolved(db, user_id, reason):
        return None
    flag = AccountFlag(user_id=user_id, reason=reason, severity=severity, details=details)
    db.add(flag)
    await db.flush()
    return flag


async def detect_for_user(db: AsyncSession, user_id: int) -> list[AccountFlag]:
    """Evaluate the fraud rules for one user, raising flags as needed."""
    now = datetime.now(timezone.utc)
    flags: list[AccountFlag] = []

    trade_since = now - timedelta(seconds=settings.FRAUD_TRADE_WINDOW)
    trades = await _count_audit(db, user_id, trade_since, "%/portfolio/%")
    if trades > settings.FRAUD_MAX_TRADES:
        flag = await _raise_flag(
            db, user_id, "rapid_trading", "high",
            {"trades": trades, "window_s": settings.FRAUD_TRADE_WINDOW},
        )
        if flag:
            flags.append(flag)

    req_since = now - timedelta(seconds=settings.FRAUD_REQUEST_WINDOW)
    requests = await _count_audit(db, user_id, req_since)
    if requests > settings.FRAUD_MAX_REQUESTS:
        flag = await _raise_flag(
            db, user_id, "request_spike", "medium",
            {"requests": requests, "window_s": settings.FRAUD_REQUEST_WINDOW},
        )
        if flag:
            flags.append(flag)

    return flags


async def scan_recent(db: AsyncSession) -> int:
    """Run detection across all users with recent audited activity."""
    window = max(settings.FRAUD_TRADE_WINDOW, settings.FRAUD_REQUEST_WINDOW)
    since = datetime.now(timezone.utc) - timedelta(seconds=window)
    rows = await db.execute(
        select(AuditLog.user_id)
        .where(AuditLog.user_id.is_not(None), AuditLog.timestamp >= since)
        .distinct()
    )
    total = 0
    for (user_id,) in rows.all():
        total += len(await detect_for_user(db, user_id))
    return total


async def list_flags(
    db: AsyncSession, resolved: bool | None = None, limit: int = 100
) -> list[AccountFlag]:
    stmt = select(AccountFlag).order_by(AccountFlag.created_at.desc())
    if resolved is not None:
        stmt = stmt.where(AccountFlag.resolved.is_(resolved))
    return list((await db.execute(stmt.limit(limit))).scalars().all())
