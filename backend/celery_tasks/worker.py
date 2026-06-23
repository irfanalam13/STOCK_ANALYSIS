"""Celery application factory.

Redis is used as both broker and result backend. The beat schedule lives in
``scheduler.py`` and is attached here.
"""
from celery import Celery

from celery_tasks.scheduler import BEAT_SCHEDULE
from core.config import settings

celery_app = Celery(
    "nepse",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "celery_tasks.tasks",
        "celery_tasks.alert_tasks",
        "celery_tasks.analytics_tasks",
        "celery_tasks.security_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    beat_schedule=BEAT_SCHEDULE,
    # Dedicated queues so evaluation, dispatch, and email delivery scale
    # independently (run workers with -Q to pin them to a subset). High-priority
    # = alerts/trading; low-priority = analytics/logs/fraud (Phase 8).
    task_routes={
        "celery_tasks.alert_tasks.evaluate_alerts": {"queue": "alert-evaluation-queue"},
        "celery_tasks.alert_tasks.dispatch_notification": {"queue": "notification-send-queue"},
        "celery_tasks.alert_tasks.deliver_email": {"queue": "email-delivery-queue"},
        "celery_tasks.analytics_tasks.refresh_analytics_snapshot": {"queue": "low-priority"},
        "celery_tasks.security_tasks.scan_fraud": {"queue": "low-priority"},
    },
)
