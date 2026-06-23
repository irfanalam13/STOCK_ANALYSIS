"""Analytics service: live market aggregations with read-through Redis caching.

All live views derive from the ``market:snapshot`` payload the broadcast stage
already caches, joined with the (separately cached) sector map. Computed
results are themselves cached for ``ANALYTICS_CACHE_TTL`` seconds so the
dashboard loads in well under a second even under load.
"""
import json

from sqlalchemy.ext.asyncio import AsyncSession

from analytics import aggregator, repository as repo
from core.config import settings
from core.redis_client import KEY_ANALYTICS, KEY_MARKET_SNAPSHOT, get_redis


async def _load_snapshot() -> list[dict]:
    try:
        raw = await get_redis().get(KEY_MARKET_SNAPSHOT)
    except Exception:
        return []  # cache down → no live snapshot; aggregations return empty state
    return json.loads(raw) if raw else []


async def _cached(name: str, producer) -> dict | list:
    """Read-through cache; computes directly if Redis is unavailable."""
    key = KEY_ANALYTICS.format(name=name)
    try:
        cached = await get_redis().get(key)
        if cached is not None:
            return json.loads(cached)
    except Exception:
        return await producer()  # best-effort: skip cache entirely

    result = await producer()
    try:
        await get_redis().set(key, json.dumps(result), ex=settings.ANALYTICS_CACHE_TTL)
    except Exception:
        pass
    return result


async def overview(db: AsyncSession) -> dict:
    async def produce():
        rows = await _load_snapshot()
        return aggregator.compute_overview(rows, settings.ANALYTICS_INDEX_BASE)
    return await _cached("overview", produce)


async def sectors(db: AsyncSession) -> list[dict]:
    async def produce():
        rows = await _load_snapshot()
        sector_map = await repo.get_sector_map(db)
        return aggregator.compute_sectors(rows, sector_map)
    return await _cached("sectors", produce)


async def movers(
    db: AsyncSession, direction: str, top: int, min_volume: int
) -> list[dict]:
    name = f"movers:{direction}:{top}:{min_volume}"

    async def produce():
        rows = await _load_snapshot()
        return aggregator.rank_movers(rows, direction, top, min_volume)
    return await _cached(name, produce)


async def heatmap(db: AsyncSession, mode: str, sector: str | None) -> list[dict]:
    name = f"heatmap:{mode}:{sector or 'all'}"

    async def produce():
        rows = await _load_snapshot()
        sector_map = await repo.get_sector_map(db)
        tiles = aggregator.build_heatmap(rows, sector_map, mode)
        if sector:
            tiles = [t for t in tiles if t["sector"].lower() == sector.lower()]
        return tiles
    return await _cached(name, produce)
