"""Redis clients for caching and pub/sub.

* ``get_redis()`` returns a shared async client (used by FastAPI + WebSocket).
* ``get_sync_redis()`` returns a sync client (used by Celery tasks).

Pub/sub is the decoupling layer between the ingestion worker and the WebSocket
event engine. The worker publishes *batched* messages (one per tick, all
symbols) to the market channels; the WS engine subscribes once and fans each
batch out to the right per-symbol client subscriptions.
"""
import redis.asyncio as aioredis
import redis as sync_redis

from core.config import settings

# ---- Pub/sub channels (ingestion worker -> WebSocket engine) ----
CHANNEL_PRICES = "market:prices"   # batched live price/change/volume updates
CHANNEL_OHLC = "market:ohlc"       # batched OHLC candle updates
CHANNEL_VOLUME = "market:volume"   # batched volume deltas
MARKET_CHANNELS = (CHANNEL_PRICES, CHANNEL_OHLC, CHANNEL_VOLUME)

# ---- Cache keys ----
KEY_QUOTE = "quote:{symbol}"          # latest quote for a symbol
KEY_MARKET_SNAPSHOT = "market:snapshot"  # full live-market snapshot (REST seed)
KEY_SEQ = "market:seq"                # monotonic publish sequence counter
KEY_REPLAY = "market:replay"          # capped list of recent price envelopes
REPLAY_MAX = 500                      # how many envelopes to retain for replay

# ---- Alerts & notifications (Phase 6) ----
# Set of symbols that currently have >=1 active alert. The evaluation engine
# intersects this with the live snapshot so a tick with no watched symbols
# never touches Postgres ("avoid full DB scans").
KEY_ALERT_SYMBOLS = "alerts:active-symbols"
KEY_ALERT_COOLDOWN = "alerts:cooldown:{alert_id}"  # per-alert silence window
KEY_ALERT_RATE = "alerts:rate:{user_id}"           # per-user notification budget
KEY_VOLUME_AVG = "alerts:volavg:{symbol}"          # cached avg volume baseline

# Per-user fan-out channel for web/push delivery (WS bridge can subscribe).
CHANNEL_NOTIFY = "notify:user:{user_id}"

# ---- Analytics dashboard (Phase 7) ----
# Short-TTL caches for computed dashboard payloads (precomputed each tick by the
# pipeline, read-through on miss) so the dashboard loads in <1s off Redis.
KEY_ANALYTICS = "analytics:{name}"          # name = overview|sectors|movers|heatmap:*
KEY_ANALYTICS_TECH = "analytics:tech:{symbol}:{tf}"  # per-symbol indicators

_async_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return a process-wide async Redis client (lazy singleton)."""
    global _async_client
    if _async_client is None:
        _async_client = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
    return _async_client


def get_sync_redis() -> sync_redis.Redis:
    """Return a fresh sync Redis client for Celery tasks."""
    return sync_redis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )


async def close_redis() -> None:
    global _async_client
    if _async_client is not None:
        await _async_client.aclose()
        _async_client = None
