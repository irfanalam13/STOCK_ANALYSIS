"""Load test for the alert evaluation engine.

Benchmarks the CPU-bound core of the engine — matching live observations
against stored alert conditions — to validate the spec's targets: thousands of
alerts per second and sub-500ms per-tick evaluation. It exercises the pure
``evaluator`` over a synthetic book of alerts and a simulated market snapshot,
so no broker, database, or SMTP server is required.

Broker enqueue and SMTP delivery are intentionally excluded: they are I/O-bound
and scale by adding workers (`--scale alerts-worker=N`); this isolates the
matching hot path that runs inside ``evaluate_alerts``.

Usage
-----
    python scripts/loadtest_alerts.py --alerts 1000000 --symbols 300 --ticks 20
    python scripts/loadtest_alerts.py -a 500000 -s 250 -t 50
"""
import argparse
import os
import statistics
import sys
import time

# Allow running directly (`python scripts/loadtest_alerts.py`) from backend/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alerts.evaluator import Observation, evaluate  # noqa: E402
from alerts.models import AlertCondition, AlertType  # noqa: E402

# Round-robin alert templates spanning all three alert types.
_TEMPLATES = [
    (AlertType.PRICE, AlertCondition.ABOVE, 600.0),
    (AlertType.PRICE, AlertCondition.BELOW, 400.0),
    (AlertType.PERCENT, AlertCondition.ABOVE, 5.0),
    (AlertType.PERCENT, AlertCondition.BELOW, -5.0),
    (AlertType.VOLUME, AlertCondition.ABOVE, 2.0),
]


def build_alerts(n: int, symbols: int) -> list[tuple]:
    """n alerts spread across `symbols` symbols, cycling the templates."""
    out = []
    for i in range(n):
        sym = f"SYM{i % symbols:04d}"
        atype, cond, thresh = _TEMPLATES[i % len(_TEMPLATES)]
        out.append((sym, atype, cond, thresh))
    return out


def build_snapshot(symbols: int) -> dict[str, Observation]:
    """One observation per symbol; values chosen so ~half the alerts fire."""
    snap = {}
    for i in range(symbols):
        sym = f"SYM{i:04d}"
        snap[sym] = Observation(
            symbol=sym,
            price=550.0 + (i % 100),          # straddles the 400/600 thresholds
            change_percent=((i % 21) - 10),   # -10%..+10%
            volume=1000 * (1 + i % 6),        # up to 6x the 1000 baseline
            avg_volume=1000.0,
        )
    return snap


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = min(len(ordered) - 1, int(round((p / 100) * (len(ordered) - 1))))
    return ordered[k]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-a", "--alerts", type=int, default=1_000_000)
    ap.add_argument("-s", "--symbols", type=int, default=300)
    ap.add_argument("-t", "--ticks", type=int, default=20)
    args = ap.parse_args()

    print(f"Building {args.alerts:,} alerts across {args.symbols} symbols ...")
    alerts = build_alerts(args.alerts, args.symbols)
    snapshot = build_snapshot(args.symbols)

    print(f"Running {args.ticks} evaluation tick(s) ...")
    tick_ms: list[float] = []
    total_fired = 0
    for _ in range(args.ticks):
        t0 = time.perf_counter()
        fired = 0
        for sym, atype, cond, thresh in alerts:
            obs = snapshot[sym]
            if evaluate(atype, cond, thresh, 0.0, obs) is not None:
                fired += 1
        tick_ms.append((time.perf_counter() - t0) * 1000)
        total_fired += fired

    mean_ms = statistics.mean(tick_ms)
    throughput = args.alerts / (mean_ms / 1000) if mean_ms else 0

    print("\n==== Alert engine load test ====")
    print(f"Alerts per tick    : {args.alerts:,}")
    print(f"Symbols            : {args.symbols}")
    print(f"Ticks              : {args.ticks}")
    print(f"Fired per tick     : ~{total_fired // args.ticks:,}")
    print(f"Per-tick latency ms: p50={pct(tick_ms,50):.1f} "
          f"p95={pct(tick_ms,95):.1f} p99={pct(tick_ms,99):.1f} "
          f"mean={mean_ms:.1f}")
    print(f"Throughput         : {throughput:,.0f} alerts/s")
    target = "PASS" if mean_ms < 500 else "OVER"
    print(f"<500ms target      : {target} (mean {mean_ms:.1f} ms)")


if __name__ == "__main__":
    main()
