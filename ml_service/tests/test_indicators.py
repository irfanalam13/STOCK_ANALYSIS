"""Tests for the technical indicators and feature engineering."""
from data.synthetic import generate_ohlcv
from features.engineering import FEATURE_COLUMNS, build_dataset, build_features
from features.indicators import rsi


def test_rsi_bounds():
    df = generate_ohlcv("NABIL", n=200)
    values = rsi(df["close"], 14)
    assert values.min() >= 0 and values.max() <= 100


def test_build_features_has_all_columns_and_no_nan():
    df = generate_ohlcv("NICA", n=300)
    feats = build_features(df)
    assert list(feats.columns) == FEATURE_COLUMNS
    assert len(feats) > 0
    assert not feats.isnull().any().any()


def test_build_dataset_labels_valid():
    df = generate_ohlcv("UPPER", n=400)
    ds = build_dataset(df)
    assert {"target_return", "target_trend", "target_vol"}.issubset(ds.columns)
    assert set(ds["target_trend"].unique()).issubset({0, 1, 2})
    assert set(ds["target_vol"].astype(int).unique()).issubset({0, 1, 2})
