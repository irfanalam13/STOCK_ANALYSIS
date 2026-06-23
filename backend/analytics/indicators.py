"""Pure technical-indicator math.

Every function takes a list of closing prices (oldest -> newest) and returns a
series aligned to the input, with ``None`` during the warm-up window where the
indicator is not yet defined. No I/O, no framework types — so the engine can be
unit-tested exhaustively and reused on any price series.

Implemented: SMA, EMA, RSI (Wilder), MACD, Bollinger Bands, plus a
``compute_all`` convenience that returns the latest value of each with derived
buy/sell signals.
"""
from __future__ import annotations

Series = list[float | None]


def sma(values: list[float], period: int) -> Series:
    """Simple moving average."""
    out: Series = [None] * len(values)
    if period <= 0:
        return out
    running = 0.0
    for i, v in enumerate(values):
        running += v
        if i >= period:
            running -= values[i - period]
        if i >= period - 1:
            out[i] = running / period
    return out


def ema(values: list[float], period: int) -> Series:
    """Exponential moving average, seeded with the SMA of the first window."""
    out: Series = [None] * len(values)
    if period <= 0 or len(values) < period:
        return out
    k = 2.0 / (period + 1)
    prev = sum(values[:period]) / period
    out[period - 1] = prev
    for i in range(period, len(values)):
        prev = (values[i] - prev) * k + prev
        out[i] = prev
    return out


def rsi(values: list[float], period: int = 14) -> Series:
    """Relative Strength Index using Wilder's smoothing."""
    out: Series = [None] * len(values)
    if len(values) <= period:
        return out

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        delta = values[i] - values[i - 1]
        gains += max(delta, 0.0)
        losses += max(-delta, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = _rsi_from(avg_gain, avg_loss)

    for i in range(period + 1, len(values)):
        delta = values[i] - values[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = _rsi_from(avg_gain, avg_loss)
    return out


def _rsi_from(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(
    values: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> dict[str, Series]:
    """MACD line, signal line, and histogram."""
    ema_fast = ema(values, fast)
    ema_slow = ema(values, slow)
    macd_line: Series = [
        (f - s) if (f is not None and s is not None) else None
        for f, s in zip(ema_fast, ema_slow)
    ]

    # Signal = EMA of the (defined) MACD values, mapped back to their indices.
    defined_idx = [i for i, v in enumerate(macd_line) if v is not None]
    defined_vals = [macd_line[i] for i in defined_idx]
    signal_line: Series = [None] * len(values)
    sig_ema = ema([v for v in defined_vals if v is not None], signal)
    for pos, idx in enumerate(defined_idx):
        signal_line[idx] = sig_ema[pos]

    histogram: Series = [
        (m - s) if (m is not None and s is not None) else None
        for m, s in zip(macd_line, signal_line)
    ]
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def bollinger_bands(
    values: list[float], period: int = 20, num_std: float = 2.0
) -> dict[str, Series]:
    """Bollinger Bands (middle = SMA, bands = ±num_std population std)."""
    middle = sma(values, period)
    upper: Series = [None] * len(values)
    lower: Series = [None] * len(values)
    for i in range(len(values)):
        if i >= period - 1 and middle[i] is not None:
            window = values[i - period + 1 : i + 1]
            mean = middle[i]
            variance = sum((x - mean) ** 2 for x in window) / period
            std = variance ** 0.5
            upper[i] = mean + num_std * std
            lower[i] = mean - num_std * std
    return {"middle": middle, "upper": upper, "lower": lower}


# --------------------------------------------------------------------------- #
# Signal interpretation
# --------------------------------------------------------------------------- #
def _last(series: Series) -> float | None:
    for v in reversed(series):
        if v is not None:
            return v
    return None


def compute_all(values: list[float]) -> dict:
    """Latest value of each indicator plus derived buy/sell signals.

    Returns a flat, JSON-friendly dict. Signals follow standard conventions:
    RSI>70 overbought (sell), <30 oversold (buy); MACD histogram sign = trend;
    price above/below SMA50/EMA20 = trend confirmation.
    """
    closes = list(values)
    price = closes[-1] if closes else None

    rsi_v = _last(rsi(closes, 14))
    macd_d = macd(closes)
    macd_v = _last(macd_d["macd"])
    macd_sig = _last(macd_d["signal"])
    macd_hist = _last(macd_d["histogram"])
    sma20 = _last(sma(closes, 20))
    sma50 = _last(sma(closes, 50))
    ema12 = _last(ema(closes, 12))
    ema26 = _last(ema(closes, 26))
    boll = bollinger_bands(closes)
    boll_u = _last(boll["upper"])
    boll_l = _last(boll["lower"])

    signals: list[dict] = []
    if rsi_v is not None:
        if rsi_v >= 70:
            signals.append({"indicator": "RSI", "signal": "SELL",
                            "note": f"RSI {rsi_v:.0f} — overbought"})
        elif rsi_v <= 30:
            signals.append({"indicator": "RSI", "signal": "BUY",
                            "note": f"RSI {rsi_v:.0f} — oversold"})
    if macd_hist is not None:
        if macd_hist > 0:
            signals.append({"indicator": "MACD", "signal": "BUY",
                            "note": "MACD above signal — bullish"})
        elif macd_hist < 0:
            signals.append({"indicator": "MACD", "signal": "SELL",
                            "note": "MACD below signal — bearish"})
    if price is not None and sma50 is not None:
        trend = "BUY" if price > sma50 else "SELL"
        signals.append({"indicator": "SMA50", "signal": trend,
                        "note": f"Price {'above' if price > sma50 else 'below'} SMA50"})

    return {
        "price": price,
        "rsi": rsi_v,
        "macd": macd_v,
        "macd_signal": macd_sig,
        "macd_histogram": macd_hist,
        "sma_20": sma20,
        "sma_50": sma50,
        "ema_12": ema12,
        "ema_26": ema26,
        "bollinger_upper": boll_u,
        "bollinger_lower": boll_l,
        "signals": signals,
    }
