import types

import pytest


@pytest.mark.asyncio
async def test_mailersend_send_custom_email_success(monkeypatch):
    from app.common.email import MailerSendNotifier as email_mod

    class DummySettings:
        API_KEY_MAILERSEND = "key"
        APP_ADMIN_MAIL = "admin@example.com"
        APP_DOMAIN = "example.com"
        APP_URL = "http://app.example"

    monkeypatch.setattr(email_mod, "settings", DummySettings)

    # Force randint to avoid BCC
    monkeypatch.setattr(email_mod, "randint", lambda a, b: 2)

    # Dummy builder with chainable API
    calls = {"from_email": None, "to_many": None, "subject": None, "template": None, "personalize_many": None, "bcc": 0, "build": 0}

    class DummyBuilder:
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

    class DummyEmailClient:
        class Emails:
            def send(self, email):
                return types.SimpleNamespace(data={"ok": True})

        def __init__(self, api_key):
            self.api_key = api_key
            self.emails = self.Emails()

    monkeypatch.setattr(email_mod, "EmailBuilder", lambda: DummyBuilder())
    monkeypatch.setattr(email_mod, "MailerSendClient", DummyEmailClient)

    notifier = email_mod.MailerSendNotifier()

    ok = await notifier.send_custom_email(
        recipient_email="user@example.com",
        recipient_name="User",
        subject="Hi",
        template_id="tpl-1",
        template_vars={"x": 1},
    )

    assert ok is True
    assert calls["from_email"] == (DummySettings.APP_ADMIN_MAIL, DummySettings.APP_DOMAIN)
    assert calls["to_many"][0]["email"] == "user@example.com"
    assert calls["subject"] == "Hi"
    assert calls["template"] == "tpl-1"
    assert calls["personalize_many"][0]["data"]["x"] == 1
    assert calls["bcc"] == 0
    assert calls["build"] == 1


@pytest.mark.asyncio
async def test_mailersend_send_custom_email_with_bcc(monkeypatch):
    from app.common.email import MailerSendNotifier as email_mod

    class DummySettings:
        API_KEY_MAILERSEND = "key"
        APP_ADMIN_MAIL = "admin@example.com"
        APP_DOMAIN = "example.com"
        APP_URL = "http://app.example"

    monkeypatch.setattr(email_mod, "settings", DummySettings)

    # Force randint to trigger BCC branch
    monkeypatch.setattr(email_mod, "randint", lambda a, b: 1)

    class DummyBuilder:
        def __init__(self):
            self.bcc_calls = 0

        def from_email(self, email, name):
            return self

        def to_many(self, arr):
            return self

        def subject(self, s):
            return self

        def template(self, t):
            return self

        def personalize_many(self, arr):
            return self

        def bcc(self, email):
            self.bcc_calls += 1
            return self

        def build(self):
            return {}

    class DummyEmailClient:
        class Emails:
            def send(self, email):
                return types.SimpleNamespace(data={"ok": True})

        def __init__(self, api_key):
            self.api_key = api_key
            self.emails = self.Emails()

    dummy_builder = DummyBuilder()

    monkeypatch.setattr(email_mod, "EmailBuilder", lambda: dummy_builder)
    monkeypatch.setattr(email_mod, "MailerSendClient", DummyEmailClient)

    notifier = email_mod.MailerSendNotifier()

    ok = await notifier.send_custom_email(
        recipient_email="user@example.com",
        recipient_name="User",
        subject="Hi",
        template_id="tpl-1",
        template_vars={"x": 1},
    )

    assert ok is True
    assert dummy_builder.bcc_calls == 1


@pytest.mark.asyncio
async def test_mailersend_send_custom_email_failure_returns_false(monkeypatch):
    from app.common.email import MailerSendNotifier as email_mod

    class DummySettings:
        API_KEY_MAILERSEND = "key"
        APP_ADMIN_MAIL = "admin@example.com"
        APP_DOMAIN = "example.com"
        APP_URL = "http://app.example"

    monkeypatch.setattr(email_mod, "settings", DummySettings)

    class DummyBuilder:
        def from_email(self, email, name):
            return self

        def to_many(self, arr):
            return self

        def subject(self, s):
            return self

        def template(self, t):
            return self

        def personalize_many(self, arr):
            return self

        def build(self):
            return {}

    class DummyEmailClient:
        class Emails:
            def send(self, email):
                raise RuntimeError("boom")

        def __init__(self, api_key):
            self.api_key = api_key
            self.emails = self.Emails()

    monkeypatch.setattr(email_mod, "EmailBuilder", lambda: DummyBuilder())
    monkeypatch.setattr(email_mod, "MailerSendClient", DummyEmailClient)

    notifier = email_mod.MailerSendNotifier()

    ok = await notifier.send_custom_email(
        recipient_email="u@example.com",
        recipient_name="U",
        subject="S",
        template_id="T",
        template_vars={},
    )

    assert ok is False


@pytest.mark.asyncio
async def test_mailersend_send_offer_imported_email_delegates(monkeypatch):
    from app.common.email import MailerSendNotifier as email_mod

    class DummySettings:
        API_KEY_MAILERSEND = "key"
        APP_ADMIN_MAIL = "admin@example.com"
        APP_DOMAIN = "example.com"
        APP_URL = "http://app.example"

    monkeypatch.setattr(email_mod, "settings", DummySettings)

    notifier = email_mod.MailerSendNotifier()

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
    assert captured["template_vars"]["website_name"] == DummySettings.APP_DOMAIN
    assert captured["subject"].startswith("Substytucja")


def test_email_factory_returns_cached_instance():
    from app.common.email.factory import get_email_notifier

    n1 = get_email_notifier()
    n2 = get_email_notifier()

    assert n1 is n2
