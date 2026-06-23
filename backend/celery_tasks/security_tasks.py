"""Background security tasks (low-priority queue).

Periodic fraud scanning runs off the request path so heavy detection never
competes with trading/alert latency. Reuses the async ``fraud.scan_recent``
engine via a short-lived event loop (Celery workers are synchronous).
"""
import asyncio
import logging

from core.database import AsyncSessionLocal
from celery_tasks.worker import celery_app
from security import fraud

logger = logging.getLogger(__name__)


@celery_app.task(name="celery_tasks.security_tasks.scan_fraud")
def scan_fraud() -> int:
    """Scan recent activity for abuse patterns; return flags raised."""

    async def _run() -> int:
        async with AsyncSessionLocal() as db:
            raised = await fraud.scan_recent(db)
            await db.commit()
            return raised

    raised = asyncio.run(_run())
    logger.info("Fraud scan raised %d flag(s)", raised)
    return raised
