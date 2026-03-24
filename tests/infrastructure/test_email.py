from unittest.mock import MagicMock

import pytest


class DummySettings:
    API_KEY_MAILERSEND = "key"
    APP_ADMIN_MAIL = "admin@example.com"
    APP_DOMAIN = "example.com"
    APP_URL = "http://app.example"


class DummyBuilderBase:
    def __init__(self):
        self.bcc_calls = 0

    def from_email(self, email, name): return self
    def to_many(self, arr): return self
    def subject(self, s): return self
    def template(self, t): return self
    def personalize_many(self, arr): return self

    def bcc(self, email):
        self.bcc_calls += 1
        return self

    def build(self): return {}


class DummyEmailClient:
    def __init__(self, api_key=None, **kwargs):
        self.api_key = api_key or kwargs.get("api_key")
        self.emails = MagicMock()
        self.emails.send.return_value = MagicMock(data={"ok": True})


@pytest.mark.asyncio
async def test_mailersend_send_custom_email_success(monkeypatch):
    from app.infrastructure.notifications.email.mailer_send_notifier import MailerSendNotifier as email_mod
    monkeypatch.setattr(email_mod, "settings", DummySettings)
    monkeypatch.setattr(email_mod, "randint", lambda *args: 2)
    calls = {"from_email": None, "to_many": None, "subject": None, "template": None, "personalize_many": None, "bcc": 0, "build": 0}

    class DummyBuilder(DummyBuilderBase):
        def from_email(self, email, name):
            calls["from_email"] = (email, name)
            return self

        def to_many(self, arr):
            calls["to_many"] = arr
            return self

        def subject(self, s):
            calls["subject"] = s
            return self

        def template(self, t):
            calls["template"] = t
            return self

        def personalize_many(self, arr):
            calls["personalize_many"] = arr
            return self

        def bcc(self, email):
            calls["bcc"] += 1
            return self

        def build(self):
            calls["build"] += 1
            return {"built": True}
    monkeypatch.setattr(email_mod, "EmailBuilder", lambda *args: DummyBuilder())
    monkeypatch.setattr(email_mod, "MailerSendClient", DummyEmailClient)
    notifier = email_mod()
    ok = await notifier.send_custom_email(
        recipient_email="user@example.com",
        recipient_name="User",
        subject="Hi",
        template_id="tpl-1",
        template_vars={"x": 1},
    )
    assert ok is True
    # settings.APP_DOMAIN is globally set to test.local in conftest.py
    assert calls["from_email"] == (DummySettings.APP_ADMIN_MAIL, "test.local")
    assert calls["to_many"][0]["email"] == "user@example.com"
    assert calls["subject"] == "Hi"
    assert calls["template"] == "tpl-1"
    assert calls["personalize_many"][0]["data"]["x"] == 1
    assert calls["bcc"] == 0
    assert calls["build"] == 1


@pytest.mark.asyncio
async def test_mailersend_send_custom_email_with_bcc(monkeypatch):
    from app.infrastructure.notifications.email.mailer_send_notifier import MailerSendNotifier as email_mod
    monkeypatch.setattr(email_mod, "settings", DummySettings)
    monkeypatch.setattr(email_mod, "randint", lambda *args: 1)
    dummy_builder_instance = DummyBuilderBase()
    monkeypatch.setattr(email_mod, "EmailBuilder", lambda *args: dummy_builder_instance)
    monkeypatch.setattr(email_mod, "MailerSendClient", DummyEmailClient)
    notifier = email_mod()
    ok = await notifier.send_custom_email(
        recipient_email="user@example.com",
        recipient_name="User",
        subject="Hi",
        template_id="tpl-1",
        template_vars={"x": 1},
    )
    assert ok is True
    assert dummy_builder_instance.bcc_calls == 1


@pytest.mark.asyncio
async def test_mailersend_send_custom_email_failure_returns_false(monkeypatch):
    from app.infrastructure.notifications.email.mailer_send_notifier import MailerSendNotifier as email_mod

    class LocalDummySettings:
        API_KEY_MAILERSEND = "key"
        APP_ADMIN_MAIL = "admin@example.com"
        APP_DOMAIN = "example.com"
        APP_URL = "http://app.example"
    monkeypatch.setattr(email_mod, "settings", LocalDummySettings)

    class DummyBuilder:
        def from_email(self, email, name): return self
        def to_many(self, arr): return self
        def subject(self, s): return self
        def template(self, t): return self
        def personalize_many(self, arr): return self
        def build(self): return {}

    class DummyEmailClient:
        def __init__(self, **kwargs):
            self.emails = MagicMock()
            self.emails.send.side_effect = RuntimeError("boom")

    monkeypatch.setattr(email_mod, "EmailBuilder", lambda *args: DummyBuilder())
    monkeypatch.setattr(email_mod, "MailerSendClient", DummyEmailClient)
    notifier = email_mod()
    ok = await notifier.send_custom_email(
        recipient_email="u@example.com", recipient_name="U", subject="S", template_id="T", template_vars={},
    )
    assert ok is False


@pytest.mark.asyncio
async def test_mailersend_send_offer_imported_email_delegates(monkeypatch):
    from app.infrastructure.notifications.email.mailer_send_notifier import MailerSendNotifier as email_mod

    class LocalDummySettings:
        API_KEY_MAILERSEND = "key"
        APP_ADMIN_MAIL = "admin@example.com"
        APP_DOMAIN = "example.com"
        APP_URL = "http://app.example"
    monkeypatch.setattr(email_mod, "settings", LocalDummySettings)
    notifier = email_mod()
    captured = {}

    async def fake_send_custom_email(**kwargs):
        captured.update(kwargs)
        return True
    monkeypatch.setattr(notifier, "send_custom_email", fake_send_custom_email)
    ok = await notifier.send_offer_imported_email("to@example.com", "To", "uuid-123", extra=5)
    assert ok is True
    assert captured["recipient_email"] == "to@example.com"
    assert captured["recipient_name"] == "To"
    assert "review-uuid-123" in captured["template_vars"]["offer_url"]
    assert captured["template_vars"]["website_name"] == "test.local"
    assert captured["subject"].startswith("Substytucja")


def test_email_factory_returns_cached_instance():
    from app.infrastructure.notifications.email.factory import get_email_notifier
    n1 = get_email_notifier()
    n2 = get_email_notifier()
    assert n1 is n2
