"""Async data access for analytics (FastAPI request path)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from market_data.models import MarketData
from stocks.models import Stock


async def get_sector_map(db: AsyncSession) -> dict[str, str | None]:
    """``symbol -> sector`` for every catalogued stock."""
    rows = (await db.execute(select(Stock.symbol, Stock.sector))).all()
    return {symbol: sector for symbol, sector in rows}


async def get_close_series(
    db: AsyncSession, symbol: str, limit: int
) -> list[tuple]:
    """Most recent ``limit`` (timestamp, close) rows, returned oldest -> newest."""
    stock_id = (
        await db.execute(select(Stock.id).where(Stock.symbol == symbol.upper()))
    ).scalar_one_or_none()
    if stock_id is None:
        return []
    rows = (
        await db.execute(
            select(MarketData.timestamp, MarketData.close_price)
            .where(MarketData.stock_id == stock_id)
            .order_by(MarketData.timestamp.desc())
            .limit(limit)
        )
    ).all()
    # Reverse to chronological order for indicator math / charting.
    return [(ts, float(close)) for ts, close in reversed(rows)]
