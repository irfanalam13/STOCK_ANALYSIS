"""Data cleaning / normalization stage of the pipeline.

Guards data integrity before anything is persisted: drops malformed rows,
enforces OHLC sanity (high >= low, prices > 0), normalizes symbols, and
de-duplicates by symbol keeping the latest timestamp.
"""
from market_data.schemas import RawQuote


def _is_valid(q: RawQuote) -> bool:
    if not q.symbol:
        return False
    prices = [q.open_price, q.high_price, q.low_price, q.close_price]
    if any(p is None or p <= 0 for p in prices):
        return False
    if q.high_price < q.low_price:
        return False
    if q.volume < 0:
        return False
    return True


def clean_quotes(raw: list[RawQuote]) -> list[RawQuote]:
    """Validate, normalize, and de-duplicate raw quotes."""
    cleaned: dict[str, RawQuote] = {}
    for q in raw:
        normalized = q.model_copy(update={"symbol": q.symbol.strip().upper()})
        if not _is_valid(normalized):
            continue
        # Keep the most recent quote per symbol.
        existing = cleaned.get(normalized.symbol)
        if existing is None or normalized.timestamp >= existing.timestamp:
            cleaned[normalized.symbol] = normalized
    return list(cleaned.values())
