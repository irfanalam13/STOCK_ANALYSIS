"""Channel abstraction over the concrete transports.

``NotificationService`` is the single seam the alert engine talks to. It renders
an ``AlertPayload`` once and routes it to the requested channel. Each method
delegates to a transport module and raises on failure so the Celery dispatch
task owns retry/fallback policy.
"""
from dataclasses import dataclass

from notifications import email as email_transport
from notifications import push as push_transport
from notifications import sms as sms_transport
from notifications import templates
from notifications.templates import AlertPayload


@dataclass(frozen=True)
class Recipient:
    """Minimal recipient view — decoupled from the ORM ``User``."""

    user_id: int
    email: str | None = None
    phone: str | None = None


class NotificationService:
    """Multi-channel dispatcher. Extend by adding a transport + method."""

    def send_email(self, user: Recipient, payload: AlertPayload) -> None:
        if not user.email:
            raise ValueError("recipient has no email address")
        email_transport.send_email(
            to=user.email,
            subject=templates.subject(payload),
            html=templates.html_body(payload),
            text=templates.text_body(payload),
        )

    def send_sms(self, user: Recipient, payload: AlertPayload) -> None:
        if not user.phone:
            raise ValueError("recipient has no phone number")
        sms_transport.send_sms(to=user.phone, message=templates.text_body(payload))

    def send_push(self, user: Recipient, payload: AlertPayload) -> None:
        push_transport.send_push(
            user_id=user.user_id,
            title=templates.subject(payload),
            body=payload.reason,
            data={
                "symbol": payload.symbol,
                "price": payload.price,
                "change_percent": payload.change_percent,
            },
        )

    def dispatch(self, channel: str, user: Recipient, payload: AlertPayload) -> None:
        """Route to the transport for ``channel`` (the enum's ``.value``)."""
        handler = {
            "email": self.send_email,
            "sms": self.send_sms,
            "push": self.send_push,
        }.get(channel)
        if handler is None:
            raise ValueError(f"unsupported channel: {channel}")
        handler(user, payload)


# Process-wide singleton (transports are stateless).
notification_service = NotificationService()
