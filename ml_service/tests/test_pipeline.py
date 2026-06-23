"""End-to-end training + registry + predictor tests."""
from constants import PRICE_MODEL, TREND_MODEL, VOLATILITY_MODEL
from data.synthetic import generate_ohlcv
from features.engineering import build_features
from models.predictors import PricePredictor, TrendPredictor
from models.registry import ModelRegistry
from training.train import train


def test_train_registers_all_models(tmp_path, monkeypatch):
    monkeypatch.setattr("training.train.settings", _settings_with(tmp_path))
    results = train(["NABIL", "NICA", "UPPER"], bars=400)

    assert set(results) == {PRICE_MODEL, TREND_MODEL, VOLATILITY_MODEL}
    reg = ModelRegistry(str(tmp_path))
    info = reg.info()
    for name in (PRICE_MODEL, TREND_MODEL, VOLATILITY_MODEL):
        assert info[name]["latest"] == "v1"


def test_trained_predictor_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr("training.train.settings", _settings_with(tmp_path))
    train(["NABIL", "NICA"], bars=400)
    reg = ModelRegistry(str(tmp_path))

    price = PricePredictor(*reg.load_latest(PRICE_MODEL))
    trend = TrendPredictor(*reg.load_latest(TREND_MODEL))

    feats = build_features(generate_ohlcv("NABIL", n=200))
    row = feats.iloc[-1]

    p = price.predict(row, last_close=520.0)
    assert p["predicted_price"] > 0 and not p["fallback"]
    assert 0 <= p["confidence"] <= 1

    t = trend.predict(row)
    assert t["label"] in {"UPTREND", "DOWNTREND", "SIDEWAYS"}
    assert abs(sum(t["probabilities"].values()) - 1.0) < 1e-3


def test_predictor_fallback_when_no_model():
    price = PricePredictor(None, None)
    out = price.predict(None, last_close=100.0)
    assert out["fallback"] is True
    assert out["predicted_price"] == 100.0


def _settings_with(tmp_path):
    """Clone settings with MODEL_DIR pointed at a temp dir."""
    from config import Settings

    return Settings(MODEL_DIR=str(tmp_path))
