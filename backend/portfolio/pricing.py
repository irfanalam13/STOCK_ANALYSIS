"""Price-fetch integration for order execution and valuation.

Resolves the current market price for a symbol with a layered strategy:
  1. Redis live quote cache (written by the market pipeline) — lowest latency.
  2. Latest persisted ``market_data`` row — durable fallback.
Raises 503 if neither is available, so an order never executes at an unknown
price.
"""
import json

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_client import KEY_QUOTE, get_redis
from market_data.models import MarketData
from stocks.models import Stock


async def _price_from_cache(symbol: str) -> float | None:
    try:
        raw = await get_redis().get(KEY_QUOTE.format(symbol=symbol.upper()))
        if not raw:
            return None
        data = json.loads(raw)
        # Cache holds the cleaned quote (close_price) or a price update (price).
        return float(data.get("close_price") or data.get("price"))
    except Exception:
        return None


async def _price_from_db(db: AsyncSession, stock_id: int) -> float | None:
    result = await db.execute(
        select(MarketData.close_price)
        .where(MarketData.stock_id == stock_id)
        .order_by(MarketData.timestamp.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return float(row) if row is not None else None


async def get_price(db: AsyncSession, stock: Stock) -> float:
    price = await _price_from_cache(stock.symbol)
    if price is None:
        price = await _price_from_db(db, stock.id)
    if price is None or price <= 0:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No market price available for {stock.symbol}",
        )
    return price
