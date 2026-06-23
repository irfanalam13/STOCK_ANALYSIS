"""Market data broadcaster: Redis pub/sub -> WebSocket engine.

Subscribes once (per API process) to the market channels, parses each batched
envelope, and hands it to the ConnectionManager for fan-out. This is the
"consumes Redis -> broadcast to subscribed clients" stage of the pipeline.

Resilience
----------
The consume loop reconnects with exponential backoff if Redis drops, so a Redis
blip degrades to "no live updates" (the frontend falls back to REST polling)
rather than a crash — the required Redis-failure fallback behaviour.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

from core.redis_client import (
    CHANNEL_OHLC,
    CHANNEL_PRICES,
    CHANNEL_VOLUME,
    MARKET_CHANNELS,
    get_redis,
)
from monitoring.metrics import metrics
from websocket.manager import manager

logger = logging.getLogger(__name__)

_MAX_BACKOFF = 10.0


class MarketBroadcaster:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stopped = False

    async def _dispatch(self, channel: str, raw: str) -> None:
        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Dropping malformed message on %s", channel)
            return
        seq = int(envelope.get("seq", 0))
        updates = envelope.get("updates", [])
        metrics.broadcaster_envelopes += 1

        if channel == CHANNEL_PRICES:
            # Track sequence gaps (dropped frames) and Redis lag on the primary
            # channel only — all three channels share one seq per tick.
            if metrics.last_seq and seq > metrics.last_seq + 1:
                metrics.broadcaster_seq_gaps += seq - metrics.last_seq - 1
            if seq:
                metrics.last_seq = max(metrics.last_seq, seq)
            ts = updates[0].get("timestamp") if updates else None
            if ts:
                lag = datetime.now(timezone.utc) - datetime.fromisoformat(ts)
                metrics.last_lag_ms = lag.total_seconds() * 1000
            await manager.route_prices(seq, updates)
        elif channel == CHANNEL_OHLC:
            await manager.route_ohlc(seq, updates)
        elif channel == CHANNEL_VOLUME:
            await manager.route_volume(seq, updates)

    async def _consume(self) -> None:
        backoff = 1.0
        while not self._stopped:
            pubsub = get_redis().pubsub()
            try:
                await pubsub.subscribe(*MARKET_CHANNELS)
                logger.info("Broadcaster subscribed to %s", list(MARKET_CHANNELS))
                backoff = 1.0  # reset after a successful (re)subscribe
                async for message in pubsub.listen():
                    if message.get("type") != "message":
                        continue
                    await self._dispatch(message["channel"], message["data"])
            except asyncio.CancelledError:
                await pubsub.aclose()
                raise
            except Exception as exc:  # noqa: BLE001 - keep the consumer alive
                metrics.broadcaster_reconnects += 1
                logger.error("Broadcaster Redis error: %s; retrying in %.0fs", exc, backoff)
                try:
                    await pubsub.aclose()
                except Exception:
                    pass
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)

    async def start(self) -> None:
        self._stopped = False
        if self._task is None:
            self._task = asyncio.create_task(self._consume())
        await manager.start_heartbeat()

    async def stop(self) -> None:
        self._stopped = True
        await manager.stop_heartbeat()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


broadcaster = MarketBroadcaster()
