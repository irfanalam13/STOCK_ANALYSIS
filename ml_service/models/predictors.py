"""Model wrappers with graceful fallback when artifacts are missing/insufficient.

Each predictor takes a single feature row (a dict / Series) and returns a plain
dict. If the model is not loaded or inputs are unusable, a deterministic
heuristic is returned with ``fallback=True`` so the API never hard-fails.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from constants import TREND_LABELS, VOL_LABELS
from features.engineering import FEATURE_COLUMNS


def _row_vector(feat_row: pd.Series) -> np.ndarray:
    return feat_row[FEATURE_COLUMNS].to_numpy(dtype=float).reshape(1, -1)


class PricePredictor:
    def __init__(self, model, meta: dict | None) -> None:
        self.model = model
        self.meta = meta or {}

    def predict(self, feat_row: pd.Series | None, last_close: float) -> dict:
        if self.model is None or feat_row is None:
            return {
                "predicted_price": round(last_close, 2),
                "predicted_return": 0.0,
                "confidence": 0.3,
                "model_version": self.meta.get("version"),
                "fallback": True,
            }
        ret = float(self.model.predict(_row_vector(feat_row))[0])
        return {
            "predicted_price": round(last_close * (1 + ret), 2),
            "predicted_return": round(ret, 5),
            # Directional accuracy from validation is a calibrated confidence.
            "confidence": round(
                float(self.meta.get("metrics", {}).get("directional_accuracy", 0.55)), 3
            ),
            "model_version": self.meta.get("version"),
            "fallback": False,
        }


class _Classifier:
    labels: list[str] = []

    def __init__(self, model, meta: dict | None) -> None:
        self.model = model
        self.meta = meta or {}

    def _fallback(self, feat_row: pd.Series | None) -> dict:  # overridden
        raise NotImplementedError

    def predict(self, feat_row: pd.Series | None) -> dict:
        if self.model is None or feat_row is None:
            return self._fallback(feat_row)
        proba = self.model.predict_proba(_row_vector(feat_row))[0]
        idx = int(np.argmax(proba))
        return {
            "label": self.labels[idx],
            "confidence": round(float(proba[idx]), 3),
            "probabilities": {
                self.labels[i]: round(float(p), 3) for i, p in enumerate(proba)
            },
            "model_version": self.meta.get("version"),
            "fallback": False,
        }


class TrendPredictor(_Classifier):
    labels = TREND_LABELS

    def _fallback(self, feat_row: pd.Series | None) -> dict:
        mom = float(feat_row["momentum_10"]) if feat_row is not None else 0.0
        label = "UPTREND" if mom > 0.01 else "DOWNTREND" if mom < -0.01 else "SIDEWAYS"
        return {"label": label, "confidence": 0.34, "probabilities": {},
                "model_version": self.meta.get("version"), "fallback": True}


class VolatilityPredictor(_Classifier):
    labels = VOL_LABELS

    def _fallback(self, feat_row: pd.Series | None) -> dict:
        vol = float(feat_row["rolling_vol_10"]) if feat_row is not None else 0.0
        label = "HIGH" if vol > 0.025 else "LOW" if vol < 0.01 else "MEDIUM"
        return {"label": label, "confidence": 0.34, "probabilities": {},
                "model_version": self.meta.get("version"), "fallback": True}
