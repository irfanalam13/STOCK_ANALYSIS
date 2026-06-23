"""Synchronous data access for the Celery evaluation/dispatch path.

The FastAPI CRUD path uses async sessions (see ``service.py``); Celery workers
are synchronous, so the engine's reads/writes live here. Queries are always
filtered by ``is_active`` and a bounded symbol set so they ride the
``ix_user_alerts_active_symbol`` index instead of scanning the table.
"""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from alerts.models import NotificationLog, NotificationStatus, UserAlert
from market_data.models import MarketData
from stocks.models import Stock


def get_active_alerts_for_symbols(
    session: Session, symbols: list[str]
) -> list[UserAlert]:
    """Active alerts whose symbol is in ``symbols`` (chunk-safe, indexed)."""
    if not symbols:
        return []
    stmt = select(UserAlert).where(
        UserAlert.is_active.is_(True),
        UserAlert.stock_symbol.in_([s.upper() for s in symbols]),
    )
    return list(session.execute(stmt).scalars().all())


def list_active_symbols(session: Session) -> list[str]:
    """Distinct symbols with at least one active alert (index-rebuild source)."""
    stmt = (
        select(UserAlert.stock_symbol)
        .where(UserAlert.is_active.is_(True))
        .distinct()
    )
    return list(session.execute(stmt).scalars().all())


def get_symbol_names(session: Session, symbols: list[str]) -> dict[str, str]:
    """Map symbol -> company_name for the alerts' symbols (for templating)."""
    if not symbols:
        return {}
    rows = session.execute(
        select(Stock.symbol, Stock.company_name).where(
            Stock.symbol.in_([s.upper() for s in symbols])
        )
    ).all()
    return {symbol: name for symbol, name in rows}


def avg_volume(session: Session, symbol: str, lookback: int) -> float | None:
    """Average volume over the last ``lookback`` rows for a symbol."""
    stock_id = session.execute(
        select(Stock.id).where(Stock.symbol == symbol.upper())
    ).scalar_one_or_none()
    if stock_id is None:
        return None
    subq = (
        select(MarketData.volume)
        .where(MarketData.stock_id == stock_id)
        .order_by(MarketData.timestamp.desc())
        .limit(lookback)
        .subquery()
    )
    avg = session.execute(select(func.avg(subq.c.volume))).scalar_one_or_none()
    return float(avg) if avg is not None else None


def mark_triggered(session: Session, alert_id: int) -> None:
    """Bump trigger metadata after an alert fires."""
    alert = session.get(UserAlert, alert_id)
    if alert is not None:
        alert.trigger_count += 1
        alert.last_triggered_at = datetime.now(timezone.utc)
        session.flush()


def create_log(
    session: Session,
    *,
    user_id: int,
    alert_id: int | None,
    symbol: str | None,
    channel,
    subject: str | None,
    message: str,
    status: NotificationStatus = NotificationStatus.PENDING,
) -> NotificationLog:
    log = NotificationLog(
        user_id=user_id,
        alert_id=alert_id,
        stock_symbol=symbol,
        channel=channel,
        subject=subject,
        message=message,
        status=status,
    )
    session.add(log)
    session.flush()
    return log


def finalize_log(
    session: Session,
    log_id: int,
    status: NotificationStatus,
    *,
    error: str | None = None,
    increment_attempts: bool = True,
) -> None:
    log = session.get(NotificationLog, log_id)
    if log is not None:
        log.status = status
        if error is not None:
            log.error = error
        if increment_attempts:
            log.attempts += 1
        session.flush()
