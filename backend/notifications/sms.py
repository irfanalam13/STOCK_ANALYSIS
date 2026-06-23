"""SMS transport (optional, Twilio-ready).

Kept dependency-free: the Twilio REST call is the only thing that would change
when ``SMS_ENABLED`` is turned on and credentials are supplied. Until then it
logs, so it can act as the documented email-failure fallback without a gateway.

Raises on failure so the dispatch task can retry / fall back.
"""
import logging

from core.config import settings

logger = logging.getLogger(__name__)


def send_sms(to: str, message: str) -> None:
    if not settings.SMS_ENABLED:
        logger.info("[sms disabled] would send to=%s: %s", to, message[:60])
        return

    # Twilio integration point. Enable by installing `twilio` and setting creds.
    try:
        from twilio.rest import Client  # imported lazily; optional dependency
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise RuntimeError("SMS_ENABLED but the `twilio` package is missing") from exc

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    client.messages.create(
        body=message, from_=settings.TWILIO_FROM_NUMBER, to=to
    )
    logger.info("Sent alert SMS to=%s", to)
