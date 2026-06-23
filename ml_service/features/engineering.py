"""Feature engineering: turn raw OHLCV into the model feature matrix + labels.

`build_features` is used at BOTH train and inference time so the feature
definition can never drift between the two.
"""
import numpy as np
import pandas as pd

from features.indicators import bollinger, ema, macd, rsi, sma

FEATURE_COLUMNS = [
    "ret_1", "ret_5", "momentum_10",
    "sma_5_ratio", "sma_10_ratio", "ema_12_ratio", "ema_26_ratio",
    "rsi_14", "macd", "macd_signal", "macd_hist",
    "bb_pct", "rolling_vol_10", "volume_change", "hl_range",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the feature matrix from an ascending OHLCV frame.

    Returns rows with all features present (warm-up rows dropped).
    """
    close = df["close"]
    out = pd.DataFrame(index=df.index)

    out["ret_1"] = close.pct_change()
    out["ret_5"] = close.pct_change(5)
    out["momentum_10"] = close / close.shift(10) - 1

    out["sma_5_ratio"] = close / sma(close, 5) - 1
    out["sma_10_ratio"] = close / sma(close, 10) - 1
    out["ema_12_ratio"] = close / ema(close, 12) - 1
    out["ema_26_ratio"] = close / ema(close, 26) - 1

    out["rsi_14"] = rsi(close, 14)
    macd_line, signal_line, hist = macd(close)
    out["macd"] = macd_line
    out["macd_signal"] = signal_line
    out["macd_hist"] = hist

    _, _, pct_b = bollinger(close, 20)
    out["bb_pct"] = pct_b

    out["rolling_vol_10"] = close.pct_change().rolling(10).std()
    out["volume_change"] = df["volume"].pct_change().replace([np.inf, -np.inf], 0)
    out["hl_range"] = (df["high"] - df["low"]) / close

    return out[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).dropna()


def build_dataset(
    df: pd.DataFrame,
    horizon: int = 5,
    trend_threshold: float = 0.02,
) -> pd.DataFrame:
    """Assemble features + supervised targets for training.

    Targets:
      * ``target_return`` — next-bar close return (regression)
      * ``target_trend``  — forward `horizon`-bar move bucketed (0/1/2)
      * ``target_vol``    — forward realized volatility bucketed by terciles
    """
    feats = build_features(df)
    close = df["close"].reindex(feats.index)

    next_ret = df["close"].shift(-1) / df["close"] - 1
    fwd_ret = df["close"].shift(-horizon) / df["close"] - 1
    fwd_vol = df["close"].pct_change().rolling(horizon).std().shift(-horizon)

    data = feats.copy()
    data["target_return"] = next_ret.reindex(feats.index)

    trend = pd.Series(1, index=feats.index)  # SIDEWAYS default
    fwd_ret = fwd_ret.reindex(feats.index)
    trend[fwd_ret > trend_threshold] = 2  # UPTREND
    trend[fwd_ret < -trend_threshold] = 0  # DOWNTREND
    data["target_trend"] = trend

    fwd_vol = fwd_vol.reindex(feats.index)
    data["target_vol"] = _bucketize(fwd_vol)
    data["_close"] = close

    return data.dropna()


def _bucketize(series: pd.Series) -> pd.Series:
    """Tercile bucket a series into 0/1/2 (LOW/MEDIUM/HIGH), robust to ties."""
    try:
        return pd.qcut(series, 3, labels=[0, 1, 2]).astype("float")
    except (ValueError, IndexError):
        lo, hi = series.quantile(0.33), series.quantile(0.66)
        return series.apply(lambda v: 0 if v <= lo else (2 if v >= hi else 1))
