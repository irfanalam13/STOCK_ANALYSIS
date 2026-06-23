"""Pure alert-evaluation logic.

Deliberately I/O-free: it takes an alert's parameters plus a single market
observation and decides whether the condition is met. Keeping it pure makes the
core trigger logic exhaustively unit-testable without Redis, Postgres, or
Celery, and lets the engine batch-evaluate millions of alerts cheaply.
"""
from dataclasses import dataclass

from alerts.models import AlertCondition, AlertType


@dataclass(frozen=True)
class Observation:
    """One symbol's live metrics, derived from a market snapshot tick."""

    symbol: str
    price: float
    change_percent: float
    volume: int
    avg_volume: float | None = None  # baseline for volume-spike alerts


def _compare(value: float, condition: AlertCondition, threshold: float,
             tolerance: float) -> bool:
    if condition == AlertCondition.ABOVE:
        return value > threshold
    if condition == AlertCondition.BELOW:
        return value < threshold
    if condition == AlertCondition.EQUAL:
        return abs(value - threshold) <= tolerance
    return False


def evaluate(
    alert_type: AlertType,
    condition: AlertCondition,
    threshold: float,
    tolerance: float,
    obs: Observation,
) -> str | None:
    """Return a human-readable trigger reason if the alert fires, else ``None``.

    * PRICE   — compares the live price against ``threshold`` (NPR).
    * PERCENT — compares intraday ``change_percent`` against ``threshold`` (%).
    * VOLUME  — fires when live volume reaches ``threshold`` × average volume.
    """
    if alert_type == AlertType.PRICE:
        if _compare(obs.price, condition, threshold, tolerance):
            return f"Price {obs.price:.2f} is {condition.value} {threshold:.2f}"
        return None

    if alert_type == AlertType.PERCENT:
        if _compare(obs.change_percent, condition, threshold, tolerance):
            return (
                f"Change {obs.change_percent:+.2f}% is {condition.value} "
                f"{threshold:.2f}%"
            )
        return None

    if alert_type == AlertType.VOLUME:
        # Without a baseline we cannot judge a spike; treat as not-triggered.
        if not obs.avg_volume or obs.avg_volume <= 0:
            return None
        ratio = obs.volume / obs.avg_volume
        if ratio >= threshold:
            return (
                f"Volume {obs.volume:,} is {ratio:.1f}× the average "
                f"({obs.avg_volume:,.0f}), threshold {threshold:.1f}×"
            )
        return None

    return None
