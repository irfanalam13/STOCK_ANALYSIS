"""Celery tasks for the alert engine and notification dispatch.

Three stages, each on its own queue so they scale independently:

    evaluate_alerts        -> alert-evaluation-queue   (CPU: match conditions)
    dispatch_notification  -> notification-send-queue  (route to a channel)
    deliver_email          -> email-delivery-queue     (I/O: SMTP, with retry)

``evaluate_alerts`` is appended to the market pipeline chain, so it runs once
per tick (event-driven, no polling). It reads the live snapshot the broadcast
stage already cached, intersects it with the Redis active-symbol index, and only
touches Postgres when there is something to evaluate.
"""
import json
import logging

from core.config import settings
from core.database import get_sync_db
from core.redis_client import KEY_MARKET_SNAPSHOT, KEY_VOLUME_AVG, get_sync_redis
from celery_tasks.worker import celery_app
from alerts import cache, repository as repo
from alerts.evaluator import Observation, evaluate
from alerts.models import AlertType, NotificationChannel, NotificationStatus
from notifications.service import Recipient, notification_service
from notifications import email as email_transport
from notifications import sms as sms_transport
from notifications import templates
from users.models import User

logger = logging.getLogger(__name__)


def _cached_avg_volume(redis, session, symbol: str) -> float | None:
    """Read a symbol's avg-volume baseline from Redis, computing on miss."""
    key = KEY_VOLUME_AVG.format(symbol=symbol)
    cached = redis.get(key)
    if cached is not None:
        return float(cached)
    avg = repo.avg_volume(session, symbol, settings.VOLUME_AVG_LOOKBACK)
    if avg is not None:
        redis.set(key, avg, ex=settings.VOLUME_AVG_CACHE_TTL)
    return avg


@celery_app.task(name="celery_tasks.alert_tasks.evaluate_alerts")
def evaluate_alerts(_prev=None) -> int:
    """Stage A: match the live snapshot against active alerts; enqueue hits.

    ``_prev`` is ignored — it only exists so this task can be chained after
    ``broadcast_updates``. State is read from Redis, not the chain payload.
    """
    redis = get_sync_redis()

    raw = redis.get(KEY_MARKET_SNAPSHOT)
    if not raw:
        return 0
    snapshot = {item["symbol"]: item for item in json.loads(raw)}

    active = cache.get_active_symbols_sync()
    if not active:
        # Cold cache (e.g. Redis flushed): rebuild the index from the DB once.
        with get_sync_db() as session:
            symbols = repo.list_active_symbols(session)
        if not symbols:
            return 0
        redis.delete(cache.KEY_ALERT_SYMBOLS)
        redis.sadd(cache.KEY_ALERT_SYMBOLS, *symbols)
        active = set(symbols)

    watched = active & snapshot.keys()
    if not watched:
        return 0

    fired = 0
    jobs: list[dict] = []
    with get_sync_db() as session:
        alerts = repo.get_active_alerts_for_symbols(session, list(watched))
        names = repo.get_symbol_names(session, list(watched))

        for alert in alerts:
            tick = snapshot.get(alert.stock_symbol)
            if tick is None:
                continue
            if cache.is_cooling_down(redis, alert.id):
                continue

            avg_vol = (
                _cached_avg_volume(redis, session, alert.stock_symbol)
                if alert.alert_type == AlertType.VOLUME
                else None
            )
            obs = Observation(
                symbol=alert.stock_symbol,
                price=float(tick["price"]),
                change_percent=float(tick["change_percent"]),
                volume=int(tick["volume"]),
                avg_volume=avg_vol,
            )
            reason = evaluate(
                alert.alert_type, alert.condition,
                alert.threshold_value, alert.tolerance, obs,
            )
            if reason is None:
                continue

            # Platform-wide anti-flood: drop (and log) if the user is over budget.
            if not cache.allow_user_notification(redis, alert.user_id):
                logger.warning("Rate limit hit for user=%s; dropping alert=%s",
                               alert.user_id, alert.id)
                continue

            cache.start_cooldown(redis, alert.id, alert.cooldown_seconds)
            repo.mark_triggered(session, alert.id)

            payload = {
                "symbol": alert.stock_symbol,
                "company_name": names.get(alert.stock_symbol, alert.stock_symbol),
                "alert_type": alert.alert_type.value,
                "reason": reason,
                "price": obs.price,
                "change_percent": obs.change_percent,
                "volume": obs.volume,
                "timestamp": tick["timestamp"],
                "label": alert.label,
            }
            log = repo.create_log(
                session,
                user_id=alert.user_id,
                alert_id=alert.id,
                symbol=alert.stock_symbol,
                channel=alert.channel,
                subject=None,
                message=reason,
            )
            jobs.append(
                {
                    "log_id": log.id,
                    "user_id": alert.user_id,
                    "channel": alert.channel.value,
                    "payload": payload,
                }
            )
            fired += 1
        # session commits here (cooldowns, trigger counts, pending logs)

    for job in jobs:
        dispatch_notification.apply_async(args=[job], queue="notification-send-queue")

    logger.info("Evaluated %d alert(s); fired %d", len(active), fired)
    return fired


@celery_app.task(name="celery_tasks.alert_tasks.dispatch_notification")
def dispatch_notification(job: dict) -> str:
    """Stage B: resolve the recipient and route to the right channel."""
    channel = job["channel"]
    payload = templates.AlertPayload(**job["payload"])

    from mobile.models import NotificationPreference
    from mobile.service import channel_allowed

    with get_sync_db() as session:
        user = session.get(User, job["user_id"])
        recipient = Recipient(
            user_id=job["user_id"],
            email=user.email if user else None,
            phone=user.phone if user else None,  # populated when SMS is enabled
        )
        # Respect the user's per-channel notification preferences (Phase 10).
        prefs = session.get(NotificationPreference, job["user_id"])
        if not channel_allowed(prefs, channel):
            repo.finalize_log(
                session, job["log_id"], NotificationStatus.FAILED,
                error=f"{channel} disabled by user preference",
            )
            return "skipped-by-preference"

    # Email is offloaded to its own retryable queue; other channels are fast.
    if channel == NotificationChannel.EMAIL.value:
        deliver_email.apply_async(
            args=[
                job["log_id"],
                job["user_id"],
                recipient.email,
                templates.subject(payload),
                templates.html_body(payload),
                templates.text_body(payload),
            ],
            queue="email-delivery-queue",
        )
        return "queued-email"

    status = NotificationStatus.SENT
    error = None
    try:
        notification_service.dispatch(channel, recipient, payload)
    except Exception as exc:  # noqa: BLE001 — record any transport failure
        status = NotificationStatus.FAILED
        error = str(exc)
        logger.exception("Dispatch failed for log=%s channel=%s", job["log_id"], channel)

    with get_sync_db() as session:
        repo.finalize_log(session, job["log_id"], status, error=error)
    return status.value


@celery_app.task(
    bind=True,
    name="celery_tasks.alert_tasks.deliver_email",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": settings.EMAIL_MAX_RETRIES},
    default_retry_delay=settings.EMAIL_RETRY_DELAY,
)
def deliver_email(
    self, log_id: int, user_id: int, to: str, subject: str, html: str, text: str
) -> str:
    """Stage C: send one email; Celery auto-retries on failure with backoff.

    When all retries are exhausted, fall back to SMS (spec: "must include
    fallback if email fails") for users who have a phone number on file.
    """
    if not to:
        with get_sync_db() as session:
            repo.finalize_log(
                session, log_id, NotificationStatus.FAILED,
                error="recipient has no email address",
            )
        _attempt_sms_fallback(user_id, subject, text)
        return "no-recipient"

    try:
        email_transport.send_email(to, subject, html, text)
    except Exception as exc:  # noqa: BLE001
        # On the final attempt, persist the failure and try the SMS fallback.
        if self.request.retries >= self.max_retries:
            with get_sync_db() as session:
                repo.finalize_log(
                    session, log_id, NotificationStatus.FAILED, error=str(exc),
                )
            _attempt_sms_fallback(user_id, subject, text)
        raise

    with get_sync_db() as session:
        repo.finalize_log(session, log_id, NotificationStatus.SENT)
    return "sent"


@celery_app.task(name="celery_tasks.alert_tasks.send_daily_digest")
def send_daily_digest() -> int:
    """Beat-scheduled: email each user a once-daily summary of their alerts.

    Reduces notification fatigue — users who prefer a roundup over per-tick
    emails still get one consolidated message. Users with no active alerts or
    no email are skipped.
    """
    from sqlalchemy import select

    from alerts.models import UserAlert

    by_user: dict[int, list[dict]] = {}
    with get_sync_db() as session:
        alerts = (
            session.execute(
                select(UserAlert)
                .where(UserAlert.is_active.is_(True))
                .order_by(UserAlert.user_id, UserAlert.stock_symbol)
            )
            .scalars()
            .all()
        )
        for a in alerts:
            by_user.setdefault(a.user_id, []).append(
                {
                    "symbol": a.stock_symbol,
                    "label": a.label,
                    "alert_type": a.alert_type.value,
                    "condition": a.condition.value,
                    "threshold_value": a.threshold_value,
                    "trigger_count": a.trigger_count,
                    "last_triggered_at": (
                        a.last_triggered_at.isoformat() if a.last_triggered_at else None
                    ),
                }
            )

        jobs: list[dict] = []
        for user_id, rows in by_user.items():
            user = session.get(User, user_id)
            if not user or not user.email:
                continue
            subject, html, text = templates.digest(rows)
            log = repo.create_log(
                session,
                user_id=user_id,
                alert_id=None,
                symbol=None,
                channel=NotificationChannel.EMAIL,
                subject=subject,
                message="daily digest",
            )
            jobs.append(
                {"log_id": log.id, "user_id": user_id, "email": user.email,
                 "subject": subject, "html": html, "text": text}
            )
        # logs commit on context exit

    for job in jobs:
        deliver_email.apply_async(
            args=[job["log_id"], job["user_id"], job["email"],
                  job["subject"], job["html"], job["text"]],
            queue="email-delivery-queue",
        )
    logger.info("Queued %d daily digest email(s)", len(jobs))
    return len(jobs)


def _attempt_sms_fallback(user_id: int, subject: str, text: str) -> None:
    """Best-effort SMS delivery after email has failed.

    No-ops silently when the user has no phone or SMS is disabled, so a failed
    email never cascades into a task error. Records its own NotificationLog row.
    """
    with get_sync_db() as session:
        user = session.get(User, user_id)
        phone = user.phone if user else None
        if not phone or not settings.SMS_ENABLED:
            return
        log = repo.create_log(
            session,
            user_id=user_id,
            alert_id=None,
            symbol=None,
            channel=NotificationChannel.SMS,
            subject=subject,
            message=text,
        )
        log_id = log.id

    status = NotificationStatus.SENT
    error = None
    try:
        sms_transport.send_sms(phone, text)
    except Exception as exc:  # noqa: BLE001
        status = NotificationStatus.FAILED
        error = str(exc)
        logger.exception("SMS fallback failed for user=%s", user_id)

    with get_sync_db() as session:
        repo.finalize_log(session, log_id, status, error=error)
