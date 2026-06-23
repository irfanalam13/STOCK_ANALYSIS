"""Celery tasks implementing the market data pipeline.

Pipeline (see DATA FLOW in the spec):

    fetch_nepse_data -> clean_market_data -> store_market_data -> broadcast_updates

Each stage is an independent task operating on JSON-serializable dicts, chained
together by ``run_market_pipeline`` (triggered by Celery Beat). Tasks use the
SYNC database/Redis clients because Celery workers are not async.
"""
import json
import logging

from celery import chain

from core.config import settings
from core.database import get_sync_db
from core.redis_client import (
    CHANNEL_OHLC,
    CHANNEL_PRICES,
    CHANNEL_VOLUME,
    KEY_MARKET_SNAPSHOT,
    KEY_QUOTE,
    KEY_REPLAY,
    KEY_SEQ,
    REPLAY_MAX,
    get_sync_redis,
)
from celery_tasks.worker import celery_app
from market_data import repository as repo
from market_data.processor import clean_quotes
from market_data.fetcher import fetch_quotes
from market_data.schemas import RawQuote, build_updates

logger = logging.getLogger(__name__)


@celery_app.task(name="celery_tasks.tasks.fetch_nepse_data")
def fetch_nepse_data() -> list[dict]:
    """Stage 1: pull the current market snapshot from the data source."""
    quotes = fetch_quotes()
    logger.info("Fetched %d raw quotes", len(quotes))
    return [q.model_dump(mode="json") for q in quotes]


@celery_app.task(name="celery_tasks.tasks.clean_market_data")
def clean_market_data(raw: list[dict]) -> list[dict]:
    """Stage 2: validate, normalize, de-duplicate."""
    quotes = [RawQuote.model_validate(item) for item in raw]
    cleaned = clean_quotes(quotes)
    logger.info("Cleaned %d -> %d quotes", len(quotes), len(cleaned))
    return [q.model_dump(mode="json") for q in cleaned]


@celery_app.task(name="celery_tasks.tasks.store_market_data")
def store_market_data(cleaned: list[dict]) -> list[dict]:
    """Stage 3: persist to PostgreSQL and cache per-symbol quotes in Redis."""
    quotes = [RawQuote.model_validate(item) for item in cleaned]

    with get_sync_db() as session:
        inserted = repo.bulk_insert_quotes(session, quotes)
    logger.info("Persisted %d market rows", inserted)

    redis = get_sync_redis()
    pipe = redis.pipeline()
    for item in cleaned:
        pipe.set(
            KEY_QUOTE.format(symbol=item["symbol"]),
            json.dumps(item),
            ex=settings.CACHE_TTL_SECONDS,
        )
    pipe.execute()

    # Pass the snapshot downstream for broadcasting.
    return cleaned


@celery_app.task(name="celery_tasks.tasks.broadcast_updates")
def broadcast_updates(cleaned: list[dict]) -> int:
    """Stage 4: normalize to stream payloads and publish to Redis channels.

    Publishing is *batched* — one envelope per channel per tick carrying every
    symbol — so the WebSocket engine fans out without being flooded by N
    individual publishes. A monotonic ``seq`` lets clients drop duplicate or
    out-of-order envelopes.
    """
    quotes = [RawQuote.model_validate(item) for item in cleaned]
    price_updates: list[dict] = []
    ohlc_updates: list[dict] = []
    volume_updates: list[dict] = []
    for q in quotes:
        price, ohlc = build_updates(q)
        price_updates.append(price.model_dump(mode="json"))
        ohlc_updates.append(ohlc.model_dump(mode="json"))
        volume_updates.append(
            {"symbol": q.symbol, "volume": q.volume,
             "timestamp": q.timestamp.isoformat()}
        )

    redis = get_sync_redis()
    seq = redis.incr(KEY_SEQ)

    # Cache the enriched snapshot for the REST /market/live fallback + seed.
    redis.set(KEY_MARKET_SNAPSHOT, json.dumps(price_updates))

    def envelope(updates: list[dict]) -> str:
        return json.dumps({"seq": seq, "updates": updates})

    prices_envelope = envelope(price_updates)
    receivers = redis.publish(CHANNEL_PRICES, prices_envelope)
    redis.publish(CHANNEL_OHLC, envelope(ohlc_updates))
    redis.publish(CHANNEL_VOLUME, envelope(volume_updates))

    # Append to the capped replay buffer for gap-recovery / audit.
    redis.lpush(KEY_REPLAY, prices_envelope)
    redis.ltrim(KEY_REPLAY, 0, REPLAY_MAX - 1)

    logger.info("Broadcast seq=%d to %d price subscriber(s)", seq, receivers)
    return receivers


@celery_app.task(name="celery_tasks.tasks.run_market_pipeline")
def run_market_pipeline() -> str:
    """Beat-triggered orchestrator: run the pipeline stages as an async chain.

    Alert evaluation and analytics precompute are appended as final links so
    they run once per tick, right after the fresh snapshot has been broadcast
    and cached — making both event-driven rather than polled. Each ignores the
    chained payload and reads the cached snapshot directly.
    """
    from celery_tasks.alert_tasks import evaluate_alerts
    from celery_tasks.analytics_tasks import refresh_analytics_snapshot

    workflow = chain(
        fetch_nepse_data.s(),
        clean_market_data.s(),
        store_market_data.s(),
        broadcast_updates.s(),
        evaluate_alerts.s(),
        refresh_analytics_snapshot.s(),
    )
    workflow.apply_async()
    return "pipeline dispatched"
