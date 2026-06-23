"""Data-access layer for stocks + market data.

Async functions serve the FastAPI read path; sync functions serve Celery
write tasks. Keeping persistence here means services/tasks stay free of raw
SQL and session juggling.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from market_data.models import MarketData
from market_data.schemas import RawQuote
from stocks.models import Stock


# --------------------------------------------------------------------------- #
# Async reads (FastAPI)
# --------------------------------------------------------------------------- #
async def get_history_by_stock(
    db: AsyncSession, stock_id: int, limit: int = 100
) -> list[MarketData]:
    result = await db.execute(
        select(MarketData)
        .where(MarketData.stock_id == stock_id)
        .order_by(MarketData.timestamp.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_history_range(
    db: AsyncSession,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 500,
) -> list[MarketData]:
    stmt = select(MarketData)
    if start:
        stmt = stmt.where(MarketData.timestamp >= start)
    if end:
        stmt = stmt.where(MarketData.timestamp <= end)
    stmt = stmt.order_by(MarketData.timestamp.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# --------------------------------------------------------------------------- #
# Sync writes (Celery)
# --------------------------------------------------------------------------- #
def get_symbol_id_map(session: Session) -> dict[str, int]:
    """Map symbol -> stock_id for fast FK resolution during bulk insert."""
    rows = session.execute(select(Stock.symbol, Stock.id)).all()
    return {symbol: stock_id for symbol, stock_id in rows}


def bulk_insert_quotes(session: Session, quotes: list[RawQuote]) -> int:
    """Persist cleaned quotes. Unknown symbols are skipped. Returns count."""
    symbol_map = get_symbol_id_map(session)
    inserted = 0
    for q in quotes:
        stock_id = symbol_map.get(q.symbol)
        if stock_id is None:
            continue
        session.add(
            MarketData(
                stock_id=stock_id,
                open_price=q.open_price,
                high_price=q.high_price,
                low_price=q.low_price,
                close_price=q.close_price,
                volume=q.volume,
                timestamp=q.timestamp,
            )
        )
        inserted += 1
    session.flush()
    return inserted


def list_symbols(session: Session) -> list[str]:
    return list(session.execute(select(Stock.symbol)).scalars().all())
