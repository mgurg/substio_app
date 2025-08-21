import httpx
from loguru import logger

from app.config import get_settings
from app.common.slack.SlackNotifierBase import SlackNotifierBase

settings = get_settings()


class SlackNotifier(SlackNotifierBase):
    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or settings.SLACK_WEBHOOK_URL
        if not self.webhook_url:
            raise ValueError("Slack webhook URL not configured")

    async def send_message(self, text: str) -> None:
        payload = {"text": text}
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(self.webhook_url, json=payload)
                resp.raise_for_status()
            except Exception as e:
                logger.warning(f"Slack notification failed: {e}")
