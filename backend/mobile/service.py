"""Mobile service layer: watchlist sync, devices, preferences, home aggregation."""
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics import aggregator
from core.config import settings
from core.redis_client import KEY_MARKET_SNAPSHOT, get_redis
from mobile.models import DeviceToken, NotificationPreference, WatchlistItem
from mobile.schemas import WatchlistSyncItem


def now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


# --------------------------------------------------------------------------- #
# Watchlist + offline sync
# --------------------------------------------------------------------------- #
async def _all_items(db: AsyncSession, user_id: int) -> list[WatchlistItem]:
    rows = await db.execute(
        select(WatchlistItem).where(WatchlistItem.user_id == user_id)
    )
    return list(rows.scalars().all())


async def _get_item(db: AsyncSession, user_id: int, symbol: str) -> WatchlistItem | None:
    rows = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user_id, WatchlistItem.symbol == symbol.upper()
        )
    )
    return rows.scalar_one_or_none()


async def active_symbols(db: AsyncSession, user_id: int) -> list[str]:
    items = await _all_items(db, user_id)
    return sorted(i.symbol for i in items if not i.deleted)


async def add_symbol(db: AsyncSession, user_id: int, symbol: str) -> WatchlistItem:
    symbol = symbol.upper()
    item = await _get_item(db, user_id, symbol)
    if item is None:
        item = WatchlistItem(user_id=user_id, symbol=symbol, updated_at=now_ms(),
                             deleted=False)
        db.add(item)
    else:
        item.deleted = False
        item.updated_at = now_ms()
    await db.flush()
    return item


async def remove_symbol(db: AsyncSession, user_id: int, symbol: str) -> None:
    item = await _get_item(db, user_id, symbol)
    if item is not None:
        item.deleted = True          # tombstone so the deletion syncs to devices
        item.updated_at = now_ms()
        await db.flush()


async def sync_watchlist(
    db: AsyncSession, user_id: int, client_items: list[WatchlistSyncItem]
) -> list[WatchlistItem]:
    """Per-item last-write-wins reconciliation between client and server.

    For each symbol the side with the greater ``updated_at`` wins (covers adds
    and tombstoned deletes). Server-only items are preserved. Returns the full
    merged state (including tombstones) so the client can converge.
    """
    by_symbol = {i.symbol: i for i in await _all_items(db, user_id)}
    for ci in client_items:
        symbol = ci.symbol.upper()
        server = by_symbol.get(symbol)
        if server is None:
            server = WatchlistItem(user_id=user_id, symbol=symbol,
                                   updated_at=ci.updated_at, deleted=ci.deleted)
            db.add(server)
            by_symbol[symbol] = server
        elif ci.updated_at > server.updated_at:
            server.updated_at = ci.updated_at
            server.deleted = ci.deleted
    await db.flush()
    return sorted(by_symbol.values(), key=lambda r: r.symbol)


# --------------------------------------------------------------------------- #
# Device tokens
# --------------------------------------------------------------------------- #
async def register_device(
    db: AsyncSession, user_id: int, token: str, platform: str
) -> DeviceToken:
    """Idempotent upsert keyed by token (re-registration just refreshes it)."""
    existing = (
        await db.execute(select(DeviceToken).where(DeviceToken.token == token))
    ).scalar_one_or_none()
    if existing is not None:
        existing.user_id = user_id
        existing.platform = platform
        existing.last_seen = datetime.now(timezone.utc)
        await db.flush()
        return existing
    device = DeviceToken(user_id=user_id, token=token, platform=platform)
    db.add(device)
    await db.flush()
    return device


async def list_devices(db: AsyncSession, user_id: int) -> list[DeviceToken]:
    rows = await db.execute(
        select(DeviceToken).where(DeviceToken.user_id == user_id)
        .order_by(DeviceToken.created_at.desc())
    )
    return list(rows.scalars().all())


async def delete_device(db: AsyncSession, user_id: int, token: str) -> bool:
    device = (
        await db.execute(
            select(DeviceToken).where(
                DeviceToken.token == token, DeviceToken.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if device is None:
        return False
    await db.delete(device)
    await db.flush()
    return True


# --------------------------------------------------------------------------- #
# Notification preferences
# --------------------------------------------------------------------------- #
async def get_preferences(db: AsyncSession, user_id: int) -> NotificationPreference:
    prefs = await db.get(NotificationPreference, user_id)
    if prefs is None:
        prefs = NotificationPreference(user_id=user_id)
        db.add(prefs)
        await db.flush()
    return prefs


async def update_preferences(
    db: AsyncSession, user_id: int, fields: dict
) -> NotificationPreference:
    prefs = await get_preferences(db, user_id)
    for key, value in fields.items():
        setattr(prefs, key, value)
    await db.flush()
    return prefs


def channel_allowed(prefs: NotificationPreference | None, channel: str) -> bool:
    """Whether a channel is enabled for a user (default-allow if unset)."""
    if prefs is None:
        return True
    return {
        "email": prefs.email_enabled,
        "sms": prefs.sms_enabled,
        "push": prefs.push_enabled,
    }.get(channel, True)


# --------------------------------------------------------------------------- #
# Aggregated mobile home (one round-trip)
# --------------------------------------------------------------------------- #
async def _snapshot_map() -> dict[str, dict]:
    try:
        raw = await get_redis().get(KEY_MARKET_SNAPSHOT)
    except Exception:
        return {}
    return {row["symbol"]: row for row in json.loads(raw)} if raw else {}


async def home(db: AsyncSession, user_id: int, auth_token: str | None) -> dict:
    """Compact dashboard payload: overview + watchlist quotes + portfolio."""
    from portfolio import service as portfolio_service  # avoid import cycle

    snapshot = await _snapshot_map()
    overview = aggregator.compute_overview(
        list(snapshot.values()), settings.ANALYTICS_INDEX_BASE
    )

    symbols = await active_symbols(db, user_id)
    watchlist = [snapshot[s] for s in symbols if s in snapshot]

    portfolio = await portfolio_service.get_or_create_default(db, user_id)
    summary = await portfolio_service.build_summary(db, portfolio, auth_token)

    prefs = await get_preferences(db, user_id)
    return {"overview": overview, "watchlist": watchlist,
            "portfolio": summary, "preferences": prefs}
