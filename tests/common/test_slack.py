import types
import pytest


@pytest.mark.asyncio
async def test_fake_slack_notifier_captures_messages():
    from app.common.slack.FakeSlackNotifier import FakeSlackNotifier

    n = FakeSlackNotifier()

    await n.send_message("hello")
    assert n.sent_messages == ["hello"]

    await n.send_rich_message({"a": 1})
    assert n.sent_payloads == [{"a": 1}]

    await n.send_new_offer_notification("Alice", "a@example.com", "desc", "uuid-1")
    assert len(n.sent_messages) == 2
    assert "New offer created by *Alice*" in n.sent_messages[-1]
    assert "<http://localhost:3000/raw/uuid-1|View Offer>" in n.sent_messages[-1]

    await n.send_new_offer_rich_notification("Bob", "b@example.com", "info", "uuid-2")
    assert len(n.sent_payloads) == 2
    blocks = n.sent_payloads[-1]["blocks"]
    assert blocks[0]["type"] == "section"
    assert "*New offer created!*" in blocks[0]["text"]["text"]
    assert any(el.get("url") == "http://localhost:3000/raw/uuid-2" for el in blocks[1]["elements"])


@pytest.mark.asyncio
async def test_slack_notifier_sends_simple_and_rich(monkeypatch):
    # Import after monkeypatch setup
    from app.common.slack import SlackNotifier as slack_mod

    # Provide fake settings
    class DummySettings:
        SLACK_WEBHOOK_URL = "https://hooks.slack.test/T000/B000/XYZ"
        APP_URL = "http://app.example"

    monkeypatch.setattr(slack_mod, "settings", DummySettings)

    # Capture requests made via httpx.AsyncClient.post
    calls = []

    class DummyResponse:
        def raise_for_status(self):
            return None

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            calls.append((url, json))
            return DummyResponse()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", DummyClient)

    notifier = slack_mod.SlackNotifier()

    await notifier.send_message("hi")
    await notifier.send_rich_message({"blocks": [1]})

    assert calls[0][0] == DummySettings.SLACK_WEBHOOK_URL
    assert calls[0][1] == {"text": "hi"}
    assert calls[1][1] == {"blocks": [1]}

    # Also verify formatted helpers use APP_URL correctly
    calls.clear()
    await notifier.send_new_offer_notification("Ann", "ann@example.com", "desc", "uuid-x")
    assert calls and "uuid-x" in calls[0][1]["text"]

    calls.clear()
    await notifier.send_new_offer_rich_notification("Tom", "tom@example.com", "dsc", "uuid-y")
    assert calls and any("uuid-y" in str(v) for v in calls[0][1].values())


def test_slack_notifier_requires_webhook(monkeypatch):
    from app.common.slack import SlackNotifier as slack_mod

    class DummySettings:
        SLACK_WEBHOOK_URL = ""
        APP_URL = "http://app.example"

    monkeypatch.setattr(slack_mod, "settings", DummySettings)

    with pytest.raises(ValueError):
        slack_mod.SlackNotifier()


def test_slack_factory_returns_instance(monkeypatch):
    from app.common.slack import SlackNotifier as slack_mod
    from app.common.slack.factory import get_slack_notifier

    class DummySettings:
        SLACK_WEBHOOK_URL = "https://hooks.slack.test/T000/B000/XYZ"
        APP_URL = "http://app.example"

    monkeypatch.setattr(slack_mod, "settings", DummySettings)

    n = get_slack_notifier()
    assert n.__class__.__name__ == "SlackNotifier"