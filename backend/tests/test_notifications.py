"""Unit tests for the notification abstraction layer and templates."""
import pytest

from notifications import service as service_mod
from notifications import templates
from notifications.service import NotificationService, Recipient
from notifications.templates import AlertPayload


def _payload(**over) -> AlertPayload:
    base = dict(
        symbol="NABIL", company_name="Nabil Bank", alert_type="price",
        reason="Price 620.00 is above 600.00", price=620.0,
        change_percent=3.5, volume=12_500, timestamp="2026-06-20T10:00:00+00:00",
    )
    base.update(over)
    return AlertPayload(**base)


def test_subject_and_bodies_contain_key_fields():
    p = _payload()
    assert "NABIL" in templates.subject(p)
    text = templates.text_body(p)
    assert "Nabil Bank" in text and "620.00" in text and "+3.50%" in text
    html = templates.html_body(p)
    assert "NABIL" in html and "<div" in html  # structured HTML body


def test_send_email_routes_to_transport(monkeypatch):
    sent = {}

    def fake_send(to, subject, html, text):
        sent.update(to=to, subject=subject, html=html, text=text)

    # Patch the transport the service imports, not the module under test.
    monkeypatch.setattr(service_mod.email_transport, "send_email", fake_send)

    svc = NotificationService()
    svc.send_email(Recipient(user_id=1, email="u@x.com"), _payload())
    assert sent["to"] == "u@x.com"
    assert "NABIL" in sent["subject"]


def test_send_email_without_address_raises():
    with pytest.raises(ValueError):
        NotificationService().send_email(Recipient(user_id=1, email=None), _payload())


def test_dispatch_unsupported_channel_raises():
    with pytest.raises(ValueError):
        NotificationService().dispatch("carrier-pigeon", Recipient(user_id=1), _payload())


def test_dispatch_routes_by_channel(monkeypatch):
    calls = []
    monkeypatch.setattr(service_mod.email_transport, "send_email",
                        lambda **k: calls.append("email"))
    svc = NotificationService()
    svc.dispatch("email", Recipient(user_id=1, email="u@x.com"), _payload())
    assert calls == ["email"]
