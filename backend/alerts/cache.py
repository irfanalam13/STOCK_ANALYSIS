"""Redis-backed indexing and anti-spam for the alert engine.

Three responsibilities, all keeping the hot path off Postgres:

1. **Active-symbol index** — a Redis set of symbols that have >=1 active alert.
   The engine intersects it with each live tick; an empty intersection skips
   the DB entirely.
2. **Per-alert cooldown** — a TTL key that silences an alert after it fires so
   a symbol hovering at a threshold can't flood the user.
3. **Per-user rate limit** — a sliding counter capping notifications per user
   per window, the platform-wide anti-flood guard.

Sync clients are used because the evaluation/dispatch path runs inside Celery.
The async helpers serve the FastAPI CRUD path so the symbol index stays fresh.
"""
from core.config import settings
from core.redis_client import (
    KEY_ALERT_COOLDOWN,
    KEY_ALERT_RATE,
    KEY_ALERT_SYMBOLS,
    get_redis,
    get_sync_redis,
)


# --------------------------------------------------------------------------- #
# Active-symbol index
# --------------------------------------------------------------------------- #
async def refresh_active_symbols(symbols: list[str]) -> None:
    """Replace the active-symbol set (FastAPI path, after a CRUD mutation)."""
    redis = get_redis()
    pipe = redis.pipeline()
    pipe.delete(KEY_ALERT_SYMBOLS)
    if symbols:
        pipe.sadd(KEY_ALERT_SYMBOLS, *symbols)
    await pipe.execute()


def get_active_symbols_sync() -> set[str]:
    """Read the active-symbol set (Celery evaluation path)."""
    return set(get_sync_redis().smembers(KEY_ALERT_SYMBOLS))


# --------------------------------------------------------------------------- #
# Per-alert cooldown
# --------------------------------------------------------------------------- #
def is_cooling_down(redis, alert_id: int) -> bool:
    return bool(redis.exists(KEY_ALERT_COOLDOWN.format(alert_id=alert_id)))


def start_cooldown(redis, alert_id: int, seconds: int) -> None:
    if seconds > 0:
        redis.set(KEY_ALERT_COOLDOWN.format(alert_id=alert_id), "1", ex=seconds)


# --------------------------------------------------------------------------- #
# Per-user rate limit (sliding window via INCR + EXPIRE)
# --------------------------------------------------------------------------- #
def allow_user_notification(redis, user_id: int) -> bool:
    """Atomically increment the user's window counter; False if over budget."""
    key = KEY_ALERT_RATE.format(user_id=user_id)
    count = redis.incr(key)
    if count == 1:
        redis.expire(key, settings.ALERT_RATE_WINDOW)
    return count <= settings.ALERT_RATE_LIMIT
