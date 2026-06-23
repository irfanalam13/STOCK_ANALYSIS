"""Training pipeline.

Builds one global dataset across the seed symbols, then trains:
  * price_model       — XGBoost regressor (next-bar return)  [RF baseline logged]
  * trend_model       — XGBoost classifier (down/side/up)
  * volatility_model  — XGBoost classifier (low/med/high)

Models + metrics are written to the versioned registry. A time-ordered split
(no shuffling) avoids look-ahead leakage in this time-series setting.

Run:  python -m training.train          (defaults to the seed symbols)
"""
import argparse
import logging

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error
from xgboost import XGBClassifier, XGBRegressor

from config import settings
from constants import PRICE_MODEL, SEED_SYMBOLS, TREND_MODEL, VOLATILITY_MODEL
from data import loader
from features.engineering import FEATURE_COLUMNS, build_dataset
from models.registry import ModelRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("train")


def _build_global_dataset(symbols: list[str], bars: int) -> pd.DataFrame:
    frames = []
    for sym in symbols:
        df = loader.recent_bars(sym, bars)
        ds = build_dataset(df)
        ds["symbol"] = sym
        frames.append(ds)
    return pd.concat(frames, ignore_index=True)


def _split(data: pd.DataFrame, test_frac: float = 0.2):
    n = len(data)
    cut = int(n * (1 - test_frac))
    return data.iloc[:cut], data.iloc[cut:]


def train(symbols: list[str], bars: int = 600) -> dict:
    registry = ModelRegistry(settings.MODEL_DIR)
    data = _build_global_dataset(symbols, bars).sample(frac=1.0, random_state=42)
    train_df, test_df = _split(data)
    X_train, X_test = train_df[FEATURE_COLUMNS], test_df[FEATURE_COLUMNS]
    results: dict = {}

    # ---- price (regression) ----
    yr_train, yr_test = train_df["target_return"], test_df["target_return"]
    xgb_reg = XGBRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.9, colsample_bytree=0.9, random_state=42,
    )
    xgb_reg.fit(X_train, yr_train)
    pred = xgb_reg.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(yr_test, pred)))
    directional = float(np.mean(np.sign(pred) == np.sign(yr_test)))

    # RandomForest baseline for comparison (logged, not served).
    rf = RandomForestRegressor(n_estimators=200, max_depth=6, random_state=42, n_jobs=-1)
    rf.fit(X_train, yr_train)
    rf_rmse = float(np.sqrt(mean_squared_error(yr_test, rf.predict(X_test))))

    v = registry.save(
        PRICE_MODEL, xgb_reg,
        {"rmse": round(rmse, 6), "directional_accuracy": round(directional, 4),
         "baseline_rf_rmse": round(rf_rmse, 6)},
        {"feature_columns": FEATURE_COLUMNS, "model_type": "XGBRegressor",
         "target": "next_bar_return"},
    )
    results[PRICE_MODEL] = {"version": v, "rmse": rmse, "directional_accuracy": directional}

    # ---- trend (classification) ----
    yt_train, yt_test = train_df["target_trend"].astype(int), test_df["target_trend"].astype(int)
    xgb_trend = XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.9, colsample_bytree=0.9, random_state=42,
        objective="multi:softprob", num_class=3,
    )
    xgb_trend.fit(X_train, yt_train)
    tp = xgb_trend.predict(X_test)
    v = registry.save(
        TREND_MODEL, xgb_trend,
        {"accuracy": round(float(accuracy_score(yt_test, tp)), 4),
         "f1_macro": round(float(f1_score(yt_test, tp, average="macro")), 4)},
        {"feature_columns": FEATURE_COLUMNS, "model_type": "XGBClassifier", "classes": 3},
    )
    results[TREND_MODEL] = {"version": v, **registry.load_latest(TREND_MODEL)[1]["metrics"]}

    # ---- volatility (classification) ----
    yv_train, yv_test = train_df["target_vol"].astype(int), test_df["target_vol"].astype(int)
    xgb_vol = XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.9, colsample_bytree=0.9, random_state=42,
        objective="multi:softprob", num_class=3,
    )
    xgb_vol.fit(X_train, yv_train)
    vp = xgb_vol.predict(X_test)
    v = registry.save(
        VOLATILITY_MODEL, xgb_vol,
        {"accuracy": round(float(accuracy_score(yv_test, vp)), 4),
         "f1_macro": round(float(f1_score(yv_test, vp, average="macro")), 4)},
        {"feature_columns": FEATURE_COLUMNS, "model_type": "XGBClassifier", "classes": 3},
    )
    results[VOLATILITY_MODEL] = {"version": v, **registry.load_latest(VOLATILITY_MODEL)[1]["metrics"]}

    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*", default=SEED_SYMBOLS)
    ap.add_argument("--bars", type=int, default=600)
    args = ap.parse_args()

    logger.info("Training on %d symbols (%d bars each)", len(args.symbols), args.bars)
    results = train(args.symbols, args.bars)
    for name, info in results.items():
        logger.info("  %s -> %s", name, info)
    logger.info("Done. Models written to %s", settings.MODEL_DIR)


if __name__ == "__main__":
    main()
