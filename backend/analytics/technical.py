"""Technical-analysis service: indicator series + signals for one symbol.

Pulls a symbol's close-price history, runs the pure ``indicators`` engine over
the requested timeframe, and returns chart-ready series plus the latest values,
derived signals, and AI interpretation. Results are cached per symbol+timeframe.
"""
import json

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from analytics import ai_insights, indicators, repository as repo
from core.config import settings
from core.redis_client import KEY_ANALYTICS_TECH, get_redis

# Timeframe -> number of recent OHLCV rows to analyze.
_TIMEFRAME_ROWS = {"1D": 60, "1W": 200, "1M": 500}


def _series(timestamps: list[str], values: list) -> list[dict]:
    return [{"timestamp": ts, "value": v} for ts, v in zip(timestamps, values)]


async def technical(db: AsyncSession, symbol: str, timeframe: str) -> dict:
    timeframe = timeframe.upper()
    if timeframe not in _TIMEFRAME_ROWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported timeframe {timeframe}; use 1D, 1W, or 1M",
        )

    key = KEY_ANALYTICS_TECH.format(symbol=symbol.upper(), tf=timeframe)
    try:
        cached = await get_redis().get(key)
        if cached is not None:
            return json.loads(cached)
    except Exception:
        pass  # cache down → compute directly below

    rows = await repo.get_close_series(db, symbol, _TIMEFRAME_ROWS[timeframe])
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No history for {symbol.upper()}",
        )
    if len(rows) < settings.ANALYTICS_MIN_HISTORY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Insufficient history for {symbol.upper()}: "
                f"{len(rows)} rows, need {settings.ANALYTICS_MIN_HISTORY}"
            ),
        )

    timestamps = [ts.isoformat() for ts, _ in rows]
    closes = [c for _, c in rows]

    macd_d = indicators.macd(closes)
    boll = indicators.bollinger_bands(closes)
    latest = indicators.compute_all(closes)

    series = {
        "close": _series(timestamps, closes),
        "sma_20": _series(timestamps, indicators.sma(closes, 20)),
        "sma_50": _series(timestamps, indicators.sma(closes, 50)),
        "ema_12": _series(timestamps, indicators.ema(closes, 12)),
        "ema_26": _series(timestamps, indicators.ema(closes, 26)),
        "rsi": _series(timestamps, indicators.rsi(closes, 14)),
        "macd": _series(timestamps, macd_d["macd"]),
        "macd_signal": _series(timestamps, macd_d["signal"]),
        "macd_histogram": _series(timestamps, macd_d["histogram"]),
        "bollinger_upper": _series(timestamps, boll["upper"]),
        "bollinger_middle": _series(timestamps, boll["middle"]),
        "bollinger_lower": _series(timestamps, boll["lower"]),
    }

    result = {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "points": len(rows),
        "latest": latest,
        "series": series,
        "insights": ai_insights.technical_insights(symbol.upper(), latest),
        "suggestion": ai_insights.suggestion(latest),
    }
    try:
        await get_redis().set(key, json.dumps(result), ex=settings.ANALYTICS_INDICATOR_TTL)
    except Exception:
        pass
    return result
