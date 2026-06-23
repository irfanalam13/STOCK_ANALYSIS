"""Celery Beat schedule.

The market pipeline runs every ``MARKET_FETCH_INTERVAL`` seconds. Run beat with:

    celery -A celery_tasks.worker.celery_app beat --loglevel=info
"""
from celery.schedules import crontab

from core.config import settings

BEAT_SCHEDULE = {
    "run-market-pipeline": {
        "task": "celery_tasks.tasks.run_market_pipeline",
        "schedule": float(settings.MARKET_FETCH_INTERVAL),
    },
    # Phase 6: once-daily alert digest at 16:30 UTC (after NEPSE close).
    "send-daily-alert-digest": {
        "task": "celery_tasks.alert_tasks.send_daily_digest",
        "schedule": crontab(hour=16, minute=30),
    },
    # Phase 8: periodic fraud/abuse scan (low-priority queue).
    "scan-fraud": {
        "task": "celery_tasks.security_tasks.scan_fraud",
        "schedule": 300.0,  # every 5 minutes
    },
}
