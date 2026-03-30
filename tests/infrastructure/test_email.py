from unittest.mock import AsyncMock, MagicMock

import pytest


class DummySettings:
    API_KEY_MAILERSEND = "key"
    APP_ADMIN_MAIL = "admin@example.com"
    APP_DOMAIN = "example.com"
    APP_URL = "http://app.example"


@pytest.mark.asyncio
async def test_should_successfully_send_custom_email_via_mailersend(monkeypatch):
    # Given
    from app.infrastructure.notifications.email.mailer_send_notifier import MailerSendNotifier as email_mod
    monkeypatch.setattr(email_mod, "settings", DummySettings)
    monkeypatch.setattr(email_mod, "randint", lambda *args: 2)

    from mailersend import EmailBuilder, MailerSendClient
    mock_builder = MagicMock(spec=EmailBuilder)
    # Configure fluent interface
    mock_builder.from_email.return_value = mock_builder
    mock_builder.to_many.return_value = mock_builder
    mock_builder.subject.return_value = mock_builder
    mock_builder.template.return_value = mock_builder
    mock_builder.personalize_many.return_value = mock_builder
    mock_builder.bcc.return_value = mock_builder
    mock_builder.build.return_value = {"built": True}

    mock_client_instance = MagicMock(spec=MailerSendClient)
    mock_client_instance.emails = MagicMock()
    mock_client_instance.emails.send.return_value = MagicMock(data={"ok": True})

    monkeypatch.setattr(email_mod, "EmailBuilder", lambda *args, **kwargs: mock_builder)
    monkeypatch.setattr(email_mod, "MailerSendClient", lambda *args, **kwargs: mock_client_instance)

    notifier = email_mod()

    # When
    ok = await notifier.send_custom_email(
        recipient_email="user@example.com",
        recipient_name="User",
        subject="Hi",
        template_id="tpl-1",
        template_vars={"x": 1},
    )

    # Then
    assert ok is True

    # Verify calls on mock_builder
    # settings.APP_DOMAIN is globally set to test.local in conftest.py
    mock_builder.from_email.assert_called_once_with(email=DummySettings.APP_ADMIN_MAIL, name="test.local")
    mock_builder.to_many.assert_called_once_with([{"email": "user@example.com", "name": "User"}])
    mock_builder.subject.assert_called_once_with("Hi")
    mock_builder.template.assert_called_once_with("tpl-1")

    # Check personalize_many args
    args, _ = mock_builder.personalize_many.call_args
    assert args[0][0]["data"]["x"] == 1
    assert mock_builder.bcc.call_count == 0
    assert mock_builder.build.call_count == 1


@pytest.mark.asyncio
async def test_should_send_custom_email_with_bcc_via_mailersend(monkeypatch):
    # Given
    from app.infrastructure.notifications.email.mailer_send_notifier import MailerSendNotifier as email_mod
    monkeypatch.setattr(email_mod, "settings", DummySettings)
    monkeypatch.setattr(email_mod, "randint", lambda *args: 1)

    from mailersend import EmailBuilder, MailerSendClient
    mock_builder = MagicMock(spec=EmailBuilder)
    mock_builder.from_email.return_value = mock_builder
    mock_builder.to_many.return_value = mock_builder
    mock_builder.subject.return_value = mock_builder
    mock_builder.template.return_value = mock_builder
    mock_builder.personalize_many.return_value = mock_builder
    mock_builder.bcc.return_value = mock_builder
    mock_builder.build.return_value = {"built": True}

    mock_client_instance = MagicMock(spec=MailerSendClient)
    mock_client_instance.emails = MagicMock()
    mock_client_instance.emails.send.return_value = MagicMock(data={"ok": True})

    monkeypatch.setattr(email_mod, "EmailBuilder", lambda *args, **kwargs: mock_builder)
    monkeypatch.setattr(email_mod, "MailerSendClient", lambda *args, **kwargs: mock_client_instance)
    notifier = email_mod()

    # When
    ok = await notifier.send_custom_email(
        recipient_email="user@example.com",
        recipient_name="User",
        subject="Hi",
        template_id="tpl-1",
        template_vars={"x": 1},
    )

    # Then
    assert ok is True
    assert mock_builder.bcc.call_count == 1


@pytest.mark.asyncio
async def test_should_return_false_when_mailersend_custom_email_fails(monkeypatch):
    # Given
    from app.infrastructure.notifications.email.mailer_send_notifier import MailerSendNotifier as email_mod

    class LocalDummySettings:
        API_KEY_MAILERSEND = "key"
        APP_ADMIN_MAIL = "admin@example.com"
        APP_DOMAIN = "example.com"
        APP_URL = "http://app.example"
    monkeypatch.setattr(email_mod, "settings", LocalDummySettings)

    from mailersend import EmailBuilder, MailerSendClient
    mock_builder = MagicMock(spec=EmailBuilder)
    mock_builder.from_email.return_value = mock_builder
    mock_builder.to_many.return_value = mock_builder
    mock_builder.subject.return_value = mock_builder
    mock_builder.template.return_value = mock_builder
    mock_builder.personalize_many.return_value = mock_builder
    mock_builder.build.return_value = {}

    mock_client_instance = MagicMock(spec=MailerSendClient)
    mock_client_instance.emails = MagicMock()
    mock_client_instance.emails.send.side_effect = RuntimeError("boom")

    monkeypatch.setattr(email_mod, "EmailBuilder", lambda *args, **kwargs: mock_builder)
    monkeypatch.setattr(email_mod, "MailerSendClient", lambda *args, **kwargs: mock_client_instance)
    notifier = email_mod()

    # When
    ok = await notifier.send_custom_email(
        recipient_email="u@example.com", recipient_name="U", subject="S", template_id="T", template_vars={},
    )

    # Then
    assert ok is False


@pytest.mark.asyncio
async def test_should_delegate_to_send_custom_email_when_sending_offer_imported_email(monkeypatch):
    # Given
    from app.infrastructure.notifications.email.mailer_send_notifier import MailerSendNotifier as email_mod

    class LocalDummySettings:
        API_KEY_MAILERSEND = "key"
        APP_ADMIN_MAIL = "admin@example.com"
        APP_DOMAIN = "example.com"
        APP_URL = "http://app.example"
    monkeypatch.setattr(email_mod, "settings", LocalDummySettings)
    notifier = email_mod()

    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr(notifier, "send_custom_email", mock_send)

    # When
    ok = await notifier.send_offer_imported_email("to@example.com", "To", "uuid-123", extra=5)

    # Then
    assert ok is True

    # Verify calls on mock_send
    _, kwargs = mock_send.call_args
    assert kwargs["recipient_email"] == "to@example.com"
    assert kwargs["recipient_name"] == "To"
    assert "review-uuid-123" in kwargs["template_vars"]["offer_url"]
    assert kwargs["template_vars"]["website_name"] == "test.local"
    assert kwargs["subject"].startswith("Substytucja")


def test_should_return_cached_instance_from_email_factory():
    # Given
    from app.infrastructure.notifications.email.factory import get_email_notifier

    # When
    n1 = get_email_notifier()
    n2 = get_email_notifier()

    # Then
    assert n1 is n2
