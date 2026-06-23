"""Unit tests for FCM push transport and channel preference gating."""
import httpx

from mobile.models import NotificationPreference
from mobile.service import channel_allowed
from notifications import push


def _prefs(**over) -> NotificationPreference:
    base = dict(user_id=1, push_enabled=True, email_enabled=True, sms_enabled=False,
                price_alerts=True, portfolio_alerts=True, news_alerts=True)
    base.update(over)
    return NotificationPreference(**base)


# ---- channel preference gating ----
def test_channel_allowed_default_when_unset():
    assert channel_allowed(None, "push") is True
    assert channel_allowed(None, "email") is True


def test_channel_allowed_respects_prefs():
    p = _prefs(push_enabled=False, sms_enabled=True)
    assert channel_allowed(p, "push") is False
    assert channel_allowed(p, "email") is True
    assert channel_allowed(p, "sms") is True


# ---- FCM transport ----
def test_send_fcm_no_tokens():
    assert push.send_fcm([], "t", "b") == 0


def test_send_fcm_disabled_is_noop(monkeypatch):
    monkeypatch.setattr(push.settings, "FCM_ENABLED", False)
    assert push.send_fcm(["tok"], "t", "b") == 0


def test_send_fcm_enabled_posts(monkeypatch):
    monkeypatch.setattr(push.settings, "FCM_ENABLED", True)
    monkeypatch.setattr(push.settings, "FCM_SERVER_KEY", "secret")
    captured = {}

    class _Resp:
        def raise_for_status(self):
            return None

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, json=json)
        return _Resp()

    monkeypatch.setattr(httpx, "post", fake_post)
    sent = push.send_fcm(["tok1", "tok2"], "Alert", "NABIL up 5%", {"symbol": "NABIL"})

    assert sent == 2
    assert captured["json"]["registration_ids"] == ["tok1", "tok2"]
    assert captured["headers"]["Authorization"] == "key=secret"


def test_send_push_is_best_effort(monkeypatch):
    # Both transports fail/no-op, but send_push must never raise.
    def boom():
        raise RuntimeError("redis down")

    monkeypatch.setattr(push, "get_sync_redis", boom)
    monkeypatch.setattr(push, "_user_tokens", lambda uid: [])
    push.send_push(1, "title", "body")  # should not raise
