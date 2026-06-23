"""Risk Service Adapter — bridges the portfolio layer to the ML service.

Responsibilities:
  * Fetch ML volatility + signal predictions (batched, one HTTP round-trip).
  * Cache per-symbol results in Redis (``risk:{symbol}``, TTL ~45s) so the ML
    service is never hammered by the portfolio UI loop.
  * Normalize into a stable per-symbol risk view.

Fails soft: if Redis or the ML service is unavailable, returns no risk data and
the portfolio still renders (badges/warnings simply omitted).

Normalized per-symbol output::

    {"symbol", "volatility_score", "trend_signal", "risk_level", "confidence"}
"""
import json
import logging

import httpx

from core.config import settings
from core.redis_client import get_redis

logger = logging.getLogger(__name__)

_KEY = "risk:{symbol}"
# Signal → additive risk impact (per spec ML signal mapping).
_SIGNAL_IMPACT = {"BUY": -0.2, "HOLD": 0.0, "SELL": 0.3}


def _risk_level(symbol_risk: float) -> str:
    if symbol_risk >= 0.66:
        return "HIGH"
    if symbol_risk >= 0.33:
        return "MEDIUM"
    return "LOW"


def _normalize(item: dict) -> dict:
    """Map a raw ML risk item into the cached/normalized schema."""
    vol = float(item.get("volatility_score", 0.5))
    impact = _SIGNAL_IMPACT.get(item.get("signal", "HOLD"), 0.0)
    symbol_risk = max(0.0, min(1.0, vol + impact))
    return {
        "symbol": item["symbol"].upper(),
        "volatility_score": round(vol, 3),
        "trend_signal": item.get("signal", "HOLD"),
        "risk_level": _risk_level(symbol_risk),
        "confidence": round(float(item.get("confidence", 0.0)), 3),
    }


def _headers(auth_token: str | None) -> dict:
    if settings.ML_API_KEY:
        return {"X-API-Key": settings.ML_API_KEY}
    if auth_token:
        return {"Authorization": f"Bearer {auth_token}"}
    return {}


async def _call_ml(symbols: list[str], auth_token: str | None) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                f"{settings.ML_SERVICE_URL}/risk/batch",
                json={"symbols": symbols},
                headers=_headers(auth_token),
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        logger.warning("Risk ML call failed for %s: %s", symbols, exc)
        return []


async def get_batch(symbols: list[str], auth_token: str | None = None) -> dict[str, dict]:
    """Return normalized risk per symbol, Redis-cached, ML on miss."""
    symbols = [s.upper() for s in symbols]
    if not symbols:
        return {}

    redis = get_redis()
    result: dict[str, dict] = {}
    missing: list[str] = []

    for sym in symbols:
        try:
            cached = await redis.get(_KEY.format(symbol=sym))
        except Exception:
            cached = None
        if cached:
            result[sym] = json.loads(cached)
        else:
            missing.append(sym)

    if missing:
        for item in await _call_ml(missing, auth_token):
            norm = _normalize(item)
            result[norm["symbol"]] = norm
            try:
                await redis.set(
                    _KEY.format(symbol=norm["symbol"]),
                    json.dumps(norm),
                    ex=settings.RISK_CACHE_TTL,
                )
            except Exception:
                pass

    return result
