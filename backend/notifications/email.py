"""SMTP email transport.

Sends a multipart (HTML + plain-text fallback) message. Retry and rate limiting
live in the Celery task layer (``email-delivery-queue``); this module's job is a
single, well-formed send attempt. When ``EMAIL_ENABLED`` is false (the default
for dev/test), the message is logged instead of sent so the pipeline is fully
exercisable without a real SMTP server.

Raises on transport failure so the calling task can trigger Celery's retry.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html: str, text: str) -> None:
    if not settings.EMAIL_ENABLED:
        logger.info("[email disabled] would send to=%s subject=%s", to, subject)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    msg["To"] = to
    # Order matters: clients render the last part they can display.
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.sendmail(settings.EMAIL_FROM, [to], msg.as_string())
    logger.info("Sent alert email to=%s subject=%s", to, subject)
