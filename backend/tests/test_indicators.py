"""Unit tests for the pure technical-indicator engine."""
from analytics import indicators as ind


def test_sma_constant_series():
    vals = [100.0] * 10
    out = ind.sma(vals, 5)
    assert out[:4] == [None] * 4          # warm-up
    assert all(v == 100.0 for v in out[4:])


def test_sma_increasing_is_increasing():
    vals = [float(i) for i in range(1, 21)]
    out = [v for v in ind.sma(vals, 5) if v is not None]
    assert out == sorted(out) and out[0] < out[-1]


def test_ema_constant_series():
    vals = [50.0] * 30
    out = ind.ema(vals, 10)
    assert out[8] is None and out[9] == 50.0
    assert all(abs(v - 50.0) < 1e-9 for v in out[9:])


def test_rsi_bounds_and_warmup():
    vals = [float(i % 7) + 100 for i in range(40)]
    out = ind.rsi(vals, 14)
    assert out[:14] == [None] * 14
    assert all(0.0 <= v <= 100.0 for v in out if v is not None)


def test_rsi_all_gains_is_100():
    vals = [float(i) for i in range(1, 40)]
    out = ind.rsi(vals, 14)
    assert ind._last(out) == 100.0


def test_rsi_all_losses_is_0():
    vals = [float(i) for i in range(40, 1, -1)]
    out = ind.rsi(vals, 14)
    assert ind._last(out) == 0.0


def test_macd_structure():
    vals = [100 + (i % 5) for i in range(60)]
    out = ind.macd(vals)
    assert set(out) == {"macd", "signal", "histogram"}
    assert all(len(out[k]) == len(vals) for k in out)


def test_bollinger_ordering():
    vals = [100 + (i % 9) for i in range(40)]
    b = ind.bollinger_bands(vals, 20, 2)
    for u, m, l in zip(b["upper"], b["middle"], b["lower"]):
        if u is not None:
            assert l <= m <= u


def test_bollinger_constant_collapses():
    vals = [42.0] * 30
    b = ind.bollinger_bands(vals, 20, 2)
    assert b["upper"][-1] == b["middle"][-1] == b["lower"][-1] == 42.0


def test_compute_all_keys_and_signals():
    vals = [float(i) for i in range(1, 80)]
    out = ind.compute_all(vals)
    for key in ("price", "rsi", "macd", "sma_20", "sma_50", "ema_12", "signals"):
        assert key in out
    assert isinstance(out["signals"], list)
    assert out["price"] == 79.0
