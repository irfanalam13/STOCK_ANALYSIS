"""Push transport: web push (Redis fan-out) + native push (FCM).

Two delivery paths from one call:

* **Web push** — publishes to the per-user Redis channel ``notify:user:{id}``;
  a WebSocket bridge / service worker delivers browser notifications now.
* **Native push** — sends to the user's registered device tokens via Firebase
  Cloud Messaging (legacy HTTP API). Gated by ``FCM_ENABLED``; logs when off so
  the flow is fully exercisable without credentials.

Runs in the synchronous Celery dispatch path, so it uses the sync DB/Redis
clients. Both paths are best-effort and isolated — one failing never blocks the
other.
"""
import json
import logging

from sqlalchemy import select

from core.config import settings
from core.database import get_sync_db
from core.redis_client import CHANNEL_NOTIFY, get_sync_redis
from mobile.models import DeviceToken

logger = logging.getLogger(__name__)


def _user_tokens(user_id: int) -> list[str]:
    try:
        with get_sync_db() as session:
            rows = session.execute(
                select(DeviceToken.token).where(DeviceToken.user_id == user_id)
            ).all()
        return [t for (t,) in rows]
    except Exception:  # noqa: BLE001
        logger.debug("could not load device tokens for user=%s", user_id)
        return []


def send_fcm(tokens: list[str], title: str, body: str, data: dict | None = None) -> int:
    """Send a notification to FCM device tokens. Returns count attempted."""
    if not tokens:
        return 0
    if not settings.FCM_ENABLED or not settings.FCM_SERVER_KEY:
        logger.info("[fcm disabled] would push to %d device(s): %s", len(tokens), title)
        return 0

    import httpx  # local import: only needed when FCM is enabled

    resp = httpx.post(
        settings.FCM_API_URL,
        headers={
            "Authorization": f"key={settings.FCM_SERVER_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "registration_ids": tokens,
            "notification": {"title": title, "body": body},
            "data": data or {},
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    logger.info("Sent FCM push to %d device(s): %s", len(tokens), title)
    return len(tokens)


def send_push(user_id: int, title: str, body: str, data: dict | None = None) -> None:
    # 1) Web push via Redis pub/sub (browser / WS bridge).
    try:
        payload = json.dumps({"title": title, "body": body, "data": data or {}})
        receivers = get_sync_redis().publish(
            CHANNEL_NOTIFY.format(user_id=user_id), payload
        )
        logger.info("Published web push for user=%s to %d subscriber(s)", user_id, receivers)
    except Exception:  # noqa: BLE001
        logger.debug("web push publish failed for user=%s", user_id)

    # 2) Native push via FCM to the user's registered devices.
    try:
        send_fcm(_user_tokens(user_id), title, body, data)
    except Exception:  # noqa: BLE001
        logger.exception("FCM push failed for user=%s", user_id)
