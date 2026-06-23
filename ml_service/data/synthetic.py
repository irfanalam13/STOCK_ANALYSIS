"""Synthetic OHLCV generator.

Produces a realistic-looking price series (geometric random walk with drift +
volatility clustering) so the ML pipeline can train and serve with zero
external data. Seeded per symbol for reproducibility.
"""
import numpy as np
import pandas as pd

from constants import BASE_PRICES


def _seed_for(symbol: str) -> int:
    return sum(ord(c) * (i + 1) for i, c in enumerate(symbol)) % (2**32)


def generate_ohlcv(symbol: str, n: int = 600) -> pd.DataFrame:
    rng = np.random.default_rng(_seed_for(symbol))
    base = BASE_PRICES.get(symbol, 300.0)

    # Volatility clustering: a slowly varying vol process.
    vol = 0.012 + 0.008 * np.abs(np.sin(np.linspace(0, 6.28 * 3, n)))
    drift = rng.normal(0.0002, 0.0004)
    shocks = rng.normal(drift, vol)
    close = base * np.exp(np.cumsum(shocks))

    open_ = np.empty(n)
    open_[0] = base
    open_[1:] = close[:-1]
    intraday = np.abs(rng.normal(0, vol)) * close
    high = np.maximum(open_, close) + intraday
    low = np.minimum(open_, close) - intraday
    volume = rng.integers(5_000, 250_000, size=n).astype(float)

    idx = pd.date_range(end=pd.Timestamp("2026-06-20"), periods=n, freq="D")
    return pd.DataFrame(
        {
            "open": np.round(open_, 2),
            "high": np.round(high, 2),
            "low": np.round(low, 2),
            "close": np.round(close, 2),
            "volume": volume,
        },
        index=idx,
    )
