"""Alert CRUD + business rules for the FastAPI request path (async).

Enforces the spec's server-side guarantees: the symbol must exist, a user can't
exceed their alert quota, and every alert is scoped to its owner. After any
mutation that can change the *set* of watched symbols, the Redis active-symbol
index is refreshed so the evaluation engine sees the change immediately.
"""
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from alerts import cache
from alerts.models import NotificationLog, UserAlert
from alerts.schemas import AlertCreate, AlertUpdate
from core.config import settings
from stocks.service import get_by_symbol


async def _refresh_index(db: AsyncSession) -> None:
    """Recompute the active-symbol set from the DB and push it to Redis."""
    result = await db.execute(
        select(UserAlert.stock_symbol)
        .where(UserAlert.is_active.is_(True))
        .distinct()
    )
    try:
        await cache.refresh_active_symbols(list(result.scalars().all()))
    except Exception:
        # Redis being momentarily unavailable must not fail the API write;
        # the index is also rebuildable by the engine's periodic refresh.
        pass


async def _count_active(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(UserAlert)
        .where(UserAlert.user_id == user_id, UserAlert.is_active.is_(True))
    )
    return int(result.scalar_one())


async def create_alert(
    db: AsyncSession, user_id: int, data: AlertCreate
) -> UserAlert:
    stock = await get_by_symbol(db, data.symbol)
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown symbol {data.symbol.upper()}",
        )

    if await _count_active(db, user_id) >= settings.ALERT_MAX_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Alert limit reached ({settings.ALERT_MAX_PER_USER})",
        )

    alert = UserAlert(
        user_id=user_id,
        stock_symbol=stock.symbol,  # normalized/uppercased by the catalog
        alert_type=data.alert_type,
        condition=data.condition,
        threshold_value=data.threshold_value,
        tolerance=data.tolerance,
        channel=data.channel,
        label=data.label,
        cooldown_seconds=data.cooldown_seconds,
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)
    await _refresh_index(db)
    return alert


async def list_alerts(db: AsyncSession, user_id: int) -> list[UserAlert]:
    result = await db.execute(
        select(UserAlert)
        .where(UserAlert.user_id == user_id)
        .order_by(UserAlert.created_at.desc())
    )
    return list(result.scalars().all())


async def get_owned_alert(
    db: AsyncSession, user_id: int, alert_id: int
) -> UserAlert:
    alert = await db.get(UserAlert, alert_id)
    if alert is None or alert.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
        )
    return alert


async def update_alert(
    db: AsyncSession, user_id: int, alert_id: int, data: AlertUpdate
) -> UserAlert:
    alert = await get_owned_alert(db, user_id, alert_id)
    fields = data.model_dump(exclude_unset=True)
    for key, value in fields.items():
        setattr(alert, key, value)
    await db.flush()
    await db.refresh(alert)
    if "is_active" in fields:
        await _refresh_index(db)
    return alert


async def delete_alert(db: AsyncSession, user_id: int, alert_id: int) -> None:
    alert = await get_owned_alert(db, user_id, alert_id)
    await db.delete(alert)
    await db.flush()
    await _refresh_index(db)


async def list_notifications(
    db: AsyncSession, user_id: int, limit: int = 100
) -> list[NotificationLog]:
    result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.user_id == user_id)
        .order_by(NotificationLog.timestamp.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
