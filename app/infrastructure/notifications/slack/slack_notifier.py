import httpx
from loguru import logger

from app.core.config import get_settings
from app.infrastructure.notifications.slack.slack_notifier_base import SlackNotifierBase

settings = get_settings()


class SlackNotifier(SlackNotifierBase):
    settings = settings

    def __init__(self):
        webhook_url = self.settings.SLACK_WEBHOOK_URL
        if not webhook_url:
            raise ValueError("Slack webhook URL not configured")
        self.webhook_url: str = webhook_url

    async def send_message(self, text: str) -> None:
        payload = {"text": text}
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(self.webhook_url, json=payload)
                resp.raise_for_status()
            except Exception as e:
                logger.warning(f"Slack notification failed: {e}")

    async def send_rich_message(self, payload: dict) -> None:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(self.webhook_url, json=payload)
                resp.raise_for_status()
            except Exception as e:
                logger.warning(f"Slack notification failed: {e}")

    def _format_offer_url(self, offer_uuid: str) -> str:
        return f"{settings.APP_URL}/raw/{offer_uuid}"

    def _format_review_url(self, offer_uuid: str) -> str:
        return f"{settings.APP_URL}/substytucje-procesowe/review-{offer_uuid}"
