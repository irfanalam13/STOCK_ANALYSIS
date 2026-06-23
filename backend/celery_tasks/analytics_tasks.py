"""Celery task that precomputes the dashboard analytics cache each tick.

Appended to the market pipeline chain so that right after a fresh snapshot is
broadcast, the common dashboard payloads (overview, sectors, top movers,
heatmaps) are recomputed and written to the same Redis keys the async API reads.
This keeps dashboard loads instant (<1s, cache hit) even on the first request,
and makes the views update in lock-step with the live market feed.

The heavy lifting is the pure ``aggregator`` functions — shared with the async
service so there is a single source of truth for the math.
"""
import json
import logging

from sqlalchemy import select

from analytics import aggregator
from core.config import settings
from core.database import get_sync_db
from core.redis_client import KEY_ANALYTICS, KEY_MARKET_SNAPSHOT, get_sync_redis
from celery_tasks.worker import celery_app
from stocks.models import Stock

logger = logging.getLogger(__name__)

# Keep precomputed entries warm a few ticks so they never expire between refreshes.
_TTL = max(settings.ANALYTICS_CACHE_TTL, settings.MARKET_FETCH_INTERVAL * 3)


@celery_app.task(name="celery_tasks.analytics_tasks.refresh_analytics_snapshot")
def refresh_analytics_snapshot(_prev=None) -> int:
    """Recompute and cache the common dashboard payloads. Returns tiles cached."""
    redis = get_sync_redis()
    raw = redis.get(KEY_MARKET_SNAPSHOT)
    if not raw:
        return 0
    rows = json.loads(raw)

    with get_sync_db() as session:
        sector_map = {
            symbol: sector
            for symbol, sector in session.execute(
                select(Stock.symbol, Stock.sector)
            ).all()
        }

    payloads = {
        "overview": aggregator.compute_overview(rows, settings.ANALYTICS_INDEX_BASE),
        "sectors": aggregator.compute_sectors(rows, sector_map),
        "movers:gainers:10:0": aggregator.rank_movers(rows, "gainers", 10, 0),
        "movers:losers:10:0": aggregator.rank_movers(rows, "losers", 10, 0),
        "movers:gainers:5:0": aggregator.rank_movers(rows, "gainers", 5, 0),
        "movers:losers:5:0": aggregator.rank_movers(rows, "losers", 5, 0),
        "heatmap:change:all": aggregator.build_heatmap(rows, sector_map, "change"),
        "heatmap:volume:all": aggregator.build_heatmap(rows, sector_map, "volume"),
    }

    pipe = redis.pipeline()
    for name, value in payloads.items():
        pipe.set(KEY_ANALYTICS.format(name=name), json.dumps(value), ex=_TTL)
    pipe.execute()

    logger.info("Refreshed %d analytics payloads from %d symbols", len(payloads), len(rows))
    return len(rows)
