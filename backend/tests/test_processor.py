"""Data pipeline validation tests for the cleaning stage."""
from datetime import datetime, timedelta, timezone

from market_data.processor import clean_quotes
from market_data.schemas import RawQuote


def _quote(symbol="NABIL", high=105, low=95, close=100, ts=None, volume=10):
    return RawQuote(
        symbol=symbol,
        open_price=100,
        high_price=high,
        low_price=low,
        close_price=close,
        volume=volume,
        timestamp=ts or datetime.now(timezone.utc),
    )


def test_drops_invalid_ohlc():
    bad = _quote(high=90, low=110)  # high < low
    assert clean_quotes([bad]) == []


def test_drops_nonpositive_price():
    assert clean_quotes([_quote(close=0)]) == []


def test_normalizes_symbol_case():
    cleaned = clean_quotes([_quote(symbol=" nabil ")])
    assert cleaned[0].symbol == "NABIL"


def test_dedupes_keeping_latest():
    now = datetime.now(timezone.utc)
    older = _quote(close=100, ts=now - timedelta(seconds=30))
    newer = _quote(close=110, ts=now)
    cleaned = clean_quotes([older, newer])
    assert len(cleaned) == 1
    assert float(cleaned[0].close_price) == 110
