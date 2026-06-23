"""ModelService — orchestrates data prep, feature building, and prediction.

Holds the loaded predictors and turns an API request (symbol + optional current
bar / history) into prediction dicts. Feature preparation is shared across price
/ trend / volatility / signal so a single request computes features once.
"""
import pandas as pd

from config import settings
from constants import PRICE_MODEL, TREND_MODEL, VOLATILITY_MODEL
from data import loader
from features.engineering import build_features
from models.predictors import PricePredictor, TrendPredictor, VolatilityPredictor
from models.registry import ModelRegistry
from models.signals import generate_signal
from schemas import OHLCV


class ModelService:
    def __init__(self) -> None:
        self.registry = ModelRegistry(settings.MODEL_DIR)
        self.reload()

    def reload(self) -> None:
        self.price = PricePredictor(*self.registry.load_latest(PRICE_MODEL))
        self.trend = TrendPredictor(*self.registry.load_latest(TREND_MODEL))
        self.volatility = VolatilityPredictor(*self.registry.load_latest(VOLATILITY_MODEL))

    # ---- feature prep -------------------------------------------------- #
    def _prepare(
        self, symbol: str, features: OHLCV | None, history: list[OHLCV] | None
    ) -> tuple[pd.Series | None, float]:
        if history:
            df = pd.DataFrame([h.model_dump() for h in history])
        else:
            df = loader.recent_bars(symbol, settings.LOOKBACK).reset_index(drop=True)

        if features is not None:
            df = pd.concat([df, pd.DataFrame([features.model_dump()])], ignore_index=True)
            last_close = features.close
        else:
            last_close = float(df["close"].iloc[-1])

        feats = build_features(df)
        row = feats.iloc[-1] if len(feats) else None
        return row, last_close

    # ---- predictions --------------------------------------------------- #
    def predict_price(self, symbol, features, history) -> dict:
        row, last_close = self._prepare(symbol, features, history)
        return {"symbol": symbol.upper(), **self.price.predict(row, last_close)}

    def predict_trend(self, symbol, features, history) -> dict:
        row, _ = self._prepare(symbol, features, history)
        r = self.trend.predict(row)
        return {"symbol": symbol.upper(), "trend": r["label"],
                "confidence": r["confidence"], "probabilities": r["probabilities"],
                "model_version": r["model_version"], "fallback": r["fallback"]}

    def predict_volatility(self, symbol, features, history) -> dict:
        row, _ = self._prepare(symbol, features, history)
        r = self.volatility.predict(row)
        return {"symbol": symbol.upper(), "volatility": r["label"],
                "confidence": r["confidence"], "probabilities": r["probabilities"],
                "model_version": r["model_version"], "fallback": r["fallback"]}

    def risk(self, symbol, features, history) -> dict:
        """Combined volatility + signal view for portfolio risk scoring.

        Computes features once and derives a numeric ``volatility_score`` in
        [0,1] from the class probabilities (P(HIGH) + 0.5·P(MEDIUM)).
        """
        row, last_close = self._prepare(symbol, features, history)
        price = self.price.predict(row, last_close)
        trend = self.trend.predict(row)
        vol = self.volatility.predict(row)
        sig = generate_signal(price, trend, vol)

        probs = vol.get("probabilities") or {}
        if probs:
            volatility_score = round(
                probs.get("HIGH", 0) * 1.0 + probs.get("MEDIUM", 0) * 0.5, 3
            )
        else:
            volatility_score = {"LOW": 0.2, "MEDIUM": 0.55, "HIGH": 0.85}.get(
                vol["label"], 0.5
            )

        return {
            "symbol": symbol.upper(),
            "volatility": vol["label"],
            "volatility_score": volatility_score,
            "signal": sig["signal"],
            "signal_strength": sig["strength"],
            "confidence": sig["confidence"],
            "predicted_return": price["predicted_return"],
            "fallback": price["fallback"] or trend["fallback"] or vol["fallback"],
        }

    def signal(self, symbol, features, history) -> dict:
        row, last_close = self._prepare(symbol, features, history)
        price = self.price.predict(row, last_close)
        trend = self.trend.predict(row)
        vol = self.volatility.predict(row)
        sig = generate_signal(price, trend, vol)
        return {
            "symbol": symbol.upper(),
            "signal": sig["signal"],
            "strength": sig["strength"],
            "confidence": sig["confidence"],
            "reason": sig["reason"],
            "details": {
                "predicted_price": price["predicted_price"],
                "predicted_return": price["predicted_return"],
                "trend": trend["label"],
                "volatility": vol["label"],
                "score": sig["score"],
                "fallback": price["fallback"] or trend["fallback"] or vol["fallback"],
            },
        }
