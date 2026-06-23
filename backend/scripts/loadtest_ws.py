"""WebSocket load test for the NEPSE real-time engine.

Spins up N concurrent clients against ``/ws/market``, subscribes each to the
ticker firehose, and measures fan-out latency (client receive time minus the
tick timestamp embedded in each price update).

Usage
-----
    python scripts/loadtest_ws.py --connections 1000 --duration 30
    python scripts/loadtest_ws.py -c 5000 -d 30 --api http://localhost:8000

Requires the backend (API + Redis + Celery worker/beat) to be running so live
ticks are flowing. ``websockets`` ships with ``uvicorn[standard]``.
"""
import argparse
import asyncio
import json
import statistics
import time
from datetime import datetime, timezone

import httpx
import websockets


async def get_token(api: str, email: str, password: str) -> str:
    async with httpx.AsyncClient(base_url=api, timeout=10) as client:
        # Register (ignore conflict) then log in.
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "role": "viewer"},
        )
        resp = await client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def client_task(
    ws_url: str, token: str, stop: asyncio.Event, latencies: list[float], counters: dict
) -> None:
    uri = f"{ws_url}?token={token}"
    try:
        async with websockets.connect(uri, open_timeout=10, ping_interval=None) as ws:
            await ws.send(json.dumps({"action": "subscribe", "channel": "ticker"}))
            counters["connected"] += 1
            while not stop.is_set():
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                msg = json.loads(raw)
                if msg.get("type") != "prices" or not msg.get("data"):
                    continue
                counters["messages"] += 1
                ts = msg["data"][0].get("timestamp")
                if ts:
                    recv = datetime.now(timezone.utc)
                    lag = (recv - datetime.fromisoformat(ts)).total_seconds() * 1000
                    latencies.append(lag)
    except Exception as exc:  # noqa: BLE001
        counters["errors"] += 1
        counters.setdefault("error_sample", str(exc))


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = min(len(ordered) - 1, int(round((p / 100) * (len(ordered) - 1))))
    return ordered[k]


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--connections", type=int, default=1000)
    ap.add_argument("-d", "--duration", type=int, default=30)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--ws", default="ws://localhost:8000/ws/market")
    ap.add_argument("--email", default="loadtest@example.com")
    ap.add_argument("--password", default="loadtest123")
    ap.add_argument("--ramp", type=float, default=5.0, help="seconds to ramp up connections")
    args = ap.parse_args()

    print(f"Authenticating against {args.api} ...")
    token = await get_token(args.api, args.email, args.password)

    stop = asyncio.Event()
    latencies: list[float] = []
    counters = {"connected": 0, "messages": 0, "errors": 0}

    print(f"Opening {args.connections} connections (ramp {args.ramp}s)...")
    tasks = []
    delay_step = args.ramp / max(args.connections, 1)
    for _ in range(args.connections):
        tasks.append(asyncio.create_task(client_task(args.ws, token, stop, latencies, counters)))
        if delay_step:
            await asyncio.sleep(delay_step)

    print(f"Streaming for {args.duration}s ...")
    t0 = time.monotonic()
    await asyncio.sleep(args.duration)
    stop.set()
    await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.monotonic() - t0

    print("\n==== Load test results ====")
    print(f"Target connections : {args.connections}")
    print(f"Connected          : {counters['connected']}")
    print(f"Errors             : {counters['errors']}"
          + (f"  ({counters.get('error_sample')})" if counters['errors'] else ""))
    print(f"Messages received  : {counters['messages']}")
    print(f"Throughput         : {counters['messages'] / elapsed:.1f} msg/s")
    if latencies:
        print(f"Fan-out latency ms : p50={pct(latencies,50):.1f} "
              f"p95={pct(latencies,95):.1f} p99={pct(latencies,99):.1f} "
              f"max={max(latencies):.1f}")
        print(f"Mean latency ms    : {statistics.mean(latencies):.1f}")
    else:
        print("No latency samples (is the Celery worker/beat publishing ticks?)")


if __name__ == "__main__":
    asyncio.run(main())
