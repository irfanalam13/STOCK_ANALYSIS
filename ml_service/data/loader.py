"""OHLCV data access with a synthetic fallback.

When ``USE_DB`` is set, history is read from the core platform's PostgreSQL
``market_data`` table; otherwise (and on any DB error) the synthetic generator
is used so the service is always functional.
"""
import logging

import pandas as pd

from config import settings
from data.synthetic import generate_ohlcv

logger = logging.getLogger(__name__)

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from sqlalchemy import create_engine

        _engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
    return _engine


def _from_db(symbol: str, n: int) -> pd.DataFrame | None:
    try:
        from sqlalchemy import text

        query = text(
            """
            SELECT md.open_price AS open, md.high_price AS high,
                   md.low_price AS low, md.close_price AS close,
                   md.volume AS volume, md.timestamp AS ts
            FROM market_data md
            JOIN stocks s ON s.id = md.stock_id
            WHERE s.symbol = :symbol
            ORDER BY md.timestamp DESC
            LIMIT :n
            """
        )
        with _get_engine().connect() as conn:
            df = pd.read_sql(query, conn, params={"symbol": symbol.upper(), "n": n})
        if df.empty:
            return None
        df = df.set_index("ts").sort_index()
        return df[["open", "high", "low", "close", "volume"]].astype(float)
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB load failed for %s (%s); using synthetic", symbol, exc)
        return None


def recent_bars(symbol: str, n: int) -> pd.DataFrame:
    """Return the most recent ``n`` bars (ascending), DB-first with fallback."""
    if settings.USE_DB:
        df = _from_db(symbol, n)
        if df is not None and len(df) >= 30:
            return df
    return generate_ohlcv(symbol, n=max(n, 600))
