from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_should_capture_messages_in_fake_slack_notifier():
    # Given
    from app.infrastructure.notifications.slack.fake_slack_notifier import FakeSlackNotifier

    n = FakeSlackNotifier()

    # When
    await n.send_message("hello")
    await n.send_rich_message({"a": 1})
    await n.send_new_offer_notification("Alice", "a@example.com", "desc", "uuid-1")
    await n.send_new_offer_rich_notification("Bob", "b@example.com", "info", "uuid-2")

    # Then
    assert n.sent_messages[0] == "hello"
    assert n.sent_payloads[0] == {"a": 1}

    assert len(n.sent_messages) == 2
    assert "New offer created by *Alice*" in n.sent_messages[-1]
    assert "<http://localhost:3000/raw/uuid-1|View Offer>" in n.sent_messages[-1]

    assert len(n.sent_payloads) == 2
    blocks = n.sent_payloads[-1]["blocks"]
    assert blocks[0]["type"] == "section"
    assert "*New offer created!*" in blocks[0]["text"]["text"]
    assert any(el.get("url") == "http://localhost:3000/raw/uuid-2" for el in blocks[1]["elements"])


@pytest.mark.asyncio
async def test_should_send_simple_and_rich_messages_via_slack_notifier(monkeypatch):
    # Given
    # Import after monkeypatch setup
    from app.infrastructure.notifications.slack.slack_notifier import SlackNotifier as slack_mod

    # Provide fake settings
    class DummySettings:
        SLACK_WEBHOOK_URL = "https://hooks.slack.test/T000/B000/XYZ"
        APP_URL = "http://app.example"

    monkeypatch.setattr(slack_mod, "settings", DummySettings)

    import httpx
    # Use AsyncMock to mock httpx.AsyncClient
    mock_client_instance = AsyncMock(spec=httpx.AsyncClient)
    # mock_client_instance.__aenter__.return_value = mock_client_instance is default for AsyncMock if configured correctly
    # But let's be explicit if needed. AsyncMock usually handles async context managers.
    mock_client_instance.__aenter__.return_value = mock_client_instance

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_client_instance.post.return_value = mock_response

    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: mock_client_instance)

    notifier = slack_mod()

    # When
    await notifier.send_message("hi")
    await notifier.send_rich_message({"blocks": [1]})

    # Then
    # Verify calls
    assert mock_client_instance.post.call_count == 2

    call1 = mock_client_instance.post.call_args_list[0]
    assert call1.args[0] == DummySettings.SLACK_WEBHOOK_URL
    assert call1.kwargs["json"] == {"text": "hi"}

    call2 = mock_client_instance.post.call_args_list[1]
    assert call2.kwargs["json"] == {"blocks": [1]}

    # Also verify formatted helpers use APP_URL correctly
    mock_client_instance.post.reset_mock()
    await notifier.send_new_offer_notification("Ann", "ann@example.com", "desc", "uuid-x")
    assert mock_client_instance.post.called
    assert "uuid-x" in mock_client_instance.post.call_args.kwargs["json"]["text"]

    mock_client_instance.post.reset_mock()
    await notifier.send_new_offer_rich_notification("Tom", "tom@example.com", "dsc", "uuid-y")
    assert mock_client_instance.post.called
    # Check if uuid-y is in the JSON payload
    payload_str = str(mock_client_instance.post.call_args.kwargs["json"])
    assert "uuid-y" in payload_str


def test_should_require_webhook_for_slack_notifier(monkeypatch):
    # Given
    from app.infrastructure.notifications.slack.slack_notifier import SlackNotifier as slack_mod

    class DummySettings:
        SLACK_WEBHOOK_URL = ""
        APP_URL = "http://app.example"

    monkeypatch.setattr(slack_mod, "settings", DummySettings)

    # When & Then
    with pytest.raises(ValueError):
        slack_mod()


def test_should_return_instance_from_slack_factory(monkeypatch):
    # Given
    from app.infrastructure.notifications.slack.factory import get_slack_notifier
    from app.infrastructure.notifications.slack.slack_notifier import SlackNotifier as slack_mod

    class DummySettings:
        SLACK_WEBHOOK_URL = "https://hooks.slack.test/T000/B000/XYZ"
        APP_URL = "http://app.example"

    monkeypatch.setattr(slack_mod, "settings", DummySettings)

    # When
    n = get_slack_notifier()

    # Then
    assert n.__class__.__name__ == "SlackNotifier"
