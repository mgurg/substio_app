from pydantic import EmailStr

from app.infrastructure.notifications.slack.slack_notifier_base import SlackNotifierBase


class FakeSlackNotifier(SlackNotifierBase):
    def __init__(self):
        self.sent_messages: list[str] = []
        self.sent_payloads: list[dict] = []

    async def send_message(self, text: str) -> None:
        self.sent_messages.append(text)

    async def send_rich_message(self, payload: dict) -> None:
        self.sent_payloads.append(payload)

    def _format_offer_url(self, offer_uuid: str) -> str:
        return f"http://localhost:3000/raw/{offer_uuid}"

    def _format_review_url(self, offer_uuid: str) -> str:
        return f"http://localhost:3000/substytucje-procesowe/review-{offer_uuid}"
