"""NEPSE data fetcher.

NEPSE does not expose a stable, official public real-time API. This module is
therefore built around a swappable source:

* If ``settings.NEPSE_API_URL`` is set, ``fetch_quotes`` performs a real HTTP
  GET and adapts the JSON via ``_parse_external_payload`` — adjust that adapter
  to match whatever upstream you wire in.
* Otherwise it falls back to ``_simulate_quotes``, a deterministic-ish random
  walk so the full pipeline runs end-to-end with zero external dependencies.

The fetcher is intentionally synchronous because it is called from Celery
workers (which are not async).
"""
import hashlib
from datetime import datetime, timezone

import httpx

from core.config import settings
from market_data.schemas import RawQuote

# Seed catalog used both to bootstrap the DB and to drive the simulator.
NEPSE_SEED_STOCKS: list[dict] = [
    {"symbol": "NABIL", "company_name": "Nabil Bank Ltd", "sector": "Commercial Bank"},
    {"symbol": "NICA", "company_name": "NIC Asia Bank Ltd", "sector": "Commercial Bank"},
    {"symbol": "NRIC", "company_name": "Nepal Reinsurance Co", "sector": "Insurance"},
    {"symbol": "UPPER", "company_name": "Upper Tamakoshi Hydropower", "sector": "Hydropower"},
    {"symbol": "NTC", "company_name": "Nepal Telecom", "sector": "Telecom"},
    {"symbol": "CHCL", "company_name": "Chilime Hydropower Co", "sector": "Hydropower"},
    {"symbol": "GBIME", "company_name": "Global IME Bank Ltd", "sector": "Commercial Bank"},
    {"symbol": "ADBL", "company_name": "Agriculture Dev Bank Ltd", "sector": "Development Bank"},
    {"symbol": "HDL", "company_name": "Himalayan Distillery Ltd", "sector": "Manufacturing"},
    {"symbol": "NLIC", "company_name": "Nepal Life Insurance Co", "sector": "Insurance"},
]

# Rough opening reference prices (NPR) per seed symbol for the simulator.
_BASE_PRICES: dict[str, float] = {
    "NABIL": 520.0, "NICA": 410.0, "NRIC": 780.0, "UPPER": 290.0, "NTC": 980.0,
    "CHCL": 470.0, "GBIME": 215.0, "ADBL": 305.0, "HDL": 1180.0, "NLIC": 640.0,
}


def _pseudo_factor(symbol: str) -> float:
    """Deterministic per-tick pseudo-random factor in roughly [-1, 1].

    Uses the current minute + symbol so values move over time without relying
    on ``random`` (kept import-free and reproducible within a minute).
    """
    minute = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    digest = hashlib.sha256(f"{symbol}:{minute}".encode()).hexdigest()
    # Take 4 hex chars -> 0..65535 -> scale to [-1, 1].
    return (int(digest[:4], 16) / 65535.0) * 2 - 1


def _simulate_quotes() -> list[RawQuote]:
    now = datetime.now(timezone.utc)
    quotes: list[RawQuote] = []
    for symbol, base in _BASE_PRICES.items():
        drift = _pseudo_factor(symbol) * base * 0.02  # ±2% intraday move
        close = round(base + drift, 2)
        high = round(max(base, close) * 1.005, 2)
        low = round(min(base, close) * 0.995, 2)
        volume = 1000 + int(abs(_pseudo_factor(symbol + "v")) * 50000)
        quotes.append(
            RawQuote(
                symbol=symbol,
                open_price=base,
                high_price=high,
                low_price=low,
                close_price=close,
                volume=volume,
                timestamp=now,
            )
        )
    return quotes


def _parse_external_payload(payload: list[dict]) -> list[RawQuote]:
    """Adapt an external NEPSE-like JSON payload into RawQuote objects.

    Adjust the key names below to match your real upstream source.
    """
    now = datetime.now(timezone.utc)
    quotes: list[RawQuote] = []
    for item in payload:
        quotes.append(
            RawQuote(
                symbol=str(item["symbol"]).upper(),
                open_price=float(item.get("open", item.get("openPrice", 0))),
                high_price=float(item.get("high", item.get("highPrice", 0))),
                low_price=float(item.get("low", item.get("lowPrice", 0))),
                close_price=float(item.get("close", item.get("lastPrice", 0))),
                volume=int(item.get("volume", item.get("totalTradedQuantity", 0))),
                timestamp=now,
            )
        )
    return quotes


def fetch_quotes() -> list[RawQuote]:
    """Fetch the current market snapshot from the configured source."""
    if not settings.NEPSE_API_URL:
        return _simulate_quotes()

    resp = httpx.get(settings.NEPSE_API_URL, timeout=10.0)
    resp.raise_for_status()
    return _parse_external_payload(resp.json())
