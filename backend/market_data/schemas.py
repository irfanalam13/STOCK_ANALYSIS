"""Market data schemas: raw ingest, persisted output, and live snapshot."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RawQuote(BaseModel):
    """Shape emitted by the fetcher before cleaning/validation."""
    symbol: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    timestamp: datetime


class MarketDataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stock_id: int
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    timestamp: datetime


class QuoteSnapshot(BaseModel):
    """Lightweight per-symbol quote used for live broadcasts and caching."""
    symbol: str
    close_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: int
    timestamp: datetime


class PriceUpdate(BaseModel):
    """Real-time price tick pushed to clients (spec: Stock Update Payload)."""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    timestamp: datetime


class OHLCUpdate(BaseModel):
    """Real-time candle update pushed to chart subscribers."""
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    interval: str = "1m"
    timestamp: datetime


def build_updates(quote: RawQuote) -> tuple[PriceUpdate, OHLCUpdate]:
    """Derive the price + OHLC stream payloads from a cleaned quote.

    Change is measured against the session open (the reference price we hold in
    the quote), giving absolute and percentage deltas in one pass.
    """
    change = round(quote.close_price - quote.open_price, 2)
    change_pct = round(
        (change / quote.open_price * 100) if quote.open_price else 0.0, 2
    )
    price = PriceUpdate(
        symbol=quote.symbol,
        price=quote.close_price,
        change=change,
        change_percent=change_pct,
        volume=quote.volume,
        timestamp=quote.timestamp,
    )
    ohlc = OHLCUpdate(
        symbol=quote.symbol,
        open=quote.open_price,
        high=quote.high_price,
        low=quote.low_price,
        close=quote.close_price,
        volume=quote.volume,
        timestamp=quote.timestamp,
    )
    return price, ohlc
