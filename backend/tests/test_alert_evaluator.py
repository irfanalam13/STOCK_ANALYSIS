"""Unit tests for the pure alert-evaluation logic (no DB/Redis/Celery)."""
from alerts.evaluator import Observation, evaluate
from alerts.models import AlertCondition, AlertType


def _obs(price=500.0, change_percent=0.0, volume=1000, avg_volume=None):
    return Observation(
        symbol="NABIL", price=price, change_percent=change_percent,
        volume=volume, avg_volume=avg_volume,
    )


# ---- Price alerts ----
def test_price_above_triggers():
    reason = evaluate(AlertType.PRICE, AlertCondition.ABOVE, 450, 0, _obs(price=500))
    assert reason and "above" in reason


def test_price_above_not_triggered():
    assert evaluate(AlertType.PRICE, AlertCondition.ABOVE, 550, 0, _obs(price=500)) is None


def test_price_below_triggers():
    assert evaluate(AlertType.PRICE, AlertCondition.BELOW, 550, 0, _obs(price=500))


def test_price_equal_within_tolerance():
    assert evaluate(AlertType.PRICE, AlertCondition.EQUAL, 500, 5, _obs(price=503))


def test_price_equal_outside_tolerance():
    assert evaluate(AlertType.PRICE, AlertCondition.EQUAL, 500, 5, _obs(price=520)) is None


# ---- Percentage-change alerts ----
def test_percent_gain_triggers():
    assert evaluate(AlertType.PERCENT, AlertCondition.ABOVE, 5, 0,
                    _obs(change_percent=7.5))


def test_percent_loss_triggers():
    assert evaluate(AlertType.PERCENT, AlertCondition.BELOW, -5, 0,
                    _obs(change_percent=-6.2))


def test_percent_below_threshold_not_triggered():
    assert evaluate(AlertType.PERCENT, AlertCondition.ABOVE, 5, 0,
                    _obs(change_percent=3.0)) is None


# ---- Volume-spike alerts ----
def test_volume_spike_triggers_at_multiplier():
    # 5000 vs avg 1000 = 5x, threshold 2x -> fires.
    reason = evaluate(AlertType.VOLUME, AlertCondition.ABOVE, 2, 0,
                      _obs(volume=5000, avg_volume=1000))
    assert reason and "×" in reason


def test_volume_spike_below_multiplier_not_triggered():
    assert evaluate(AlertType.VOLUME, AlertCondition.ABOVE, 5, 0,
                    _obs(volume=3000, avg_volume=1000)) is None


def test_volume_without_baseline_never_triggers():
    assert evaluate(AlertType.VOLUME, AlertCondition.ABOVE, 2, 0,
                    _obs(volume=999_999, avg_volume=None)) is None
