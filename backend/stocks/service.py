"""Stock catalog logic with Redis read-through caching."""
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_client import get_redis
from stocks.models import Stock
from stocks.schemas import StockCreate

_LIST_CACHE_KEY = "stocks:all"
_LIST_CACHE_TTL = 300  # the catalog changes rarely; 5-minute cache is safe


async def list_stocks(db: AsyncSession) -> list[Stock]:
    result = await db.execute(select(Stock).order_by(Stock.symbol))
    return list(result.scalars().all())


async def get_by_symbol(db: AsyncSession, symbol: str) -> Stock | None:
    result = await db.execute(
        select(Stock).where(Stock.symbol == symbol.upper())
    )
    return result.scalar_one_or_none()


async def create_stock(db: AsyncSession, data: StockCreate) -> Stock:
    stock = Stock(
        symbol=data.symbol.upper(),
        company_name=data.company_name,
        sector=data.sector,
    )
    db.add(stock)
    await db.flush()
    await db.refresh(stock)
    # Invalidate the cached catalog so the new symbol shows up immediately.
    await get_redis().delete(_LIST_CACHE_KEY)
    return stock


async def list_stocks_cached(db: AsyncSession) -> list[dict]:
    """Read-through cache for the (rarely changing) stock catalog."""
    redis = get_redis()
    cached = await redis.get(_LIST_CACHE_KEY)
    if cached:
        return json.loads(cached)

    stocks = await list_stocks(db)
    payload = [
        {
            "id": s.id,
            "symbol": s.symbol,
            "company_name": s.company_name,
            "sector": s.sector,
        }
        for s in stocks
    ]
    await redis.set(_LIST_CACHE_KEY, json.dumps(payload), ex=_LIST_CACHE_TTL)
    return payload
