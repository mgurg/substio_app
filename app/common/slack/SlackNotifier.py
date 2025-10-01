import httpx
from loguru import logger
from pydantic import EmailStr

from app.common.slack.SlackNotifierBase import SlackNotifierBase
from app.config import get_settings

settings = get_settings()


class SlackNotifier(SlackNotifierBase):
    def __init__(self):
        self.webhook_url = settings.SLACK_WEBHOOK_URL
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

    async def send_rich_message(self, payload: dict) -> None:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(self.webhook_url, json=payload)
                resp.raise_for_status()
            except Exception as e:
                logger.warning(f"Slack notification failed: {e}")

    async def send_new_offer_notification(self, author: str, email: EmailStr, description: str, offer_uuid: str) -> None:
        """Send a formatted notification for a new offer."""
        offer_url = f"{settings.APP_URL}/raw/{offer_uuid}"
        review_url = f"{settings.APP_URL}/substytucje-procesowe/review-{offer_uuid}"

        message = (
            f":tada: New offer created by *{author}* \n"
            f"email: {email}\n"
            f"description: {description}.\n"
            f"<{offer_url}|View Offer>\n"
            f"<{review_url}|Review Offer>"
        )

        await self.send_message(message)

    async def send_new_offer_rich_notification(self, author: str, email: EmailStr, description: str, offer_uuid: str) -> None:
        """Send a formatted interactive notification for a new offer."""
        offer_url = f"{settings.APP_URL}/raw/{offer_uuid}"
        review_url = f"{settings.APP_URL}/substytucje-procesowe/review-{offer_uuid}"

        payload = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":tada: *New offer created!* \n\n*Author:* {author}\n*Email:* {email}\n*Description:* {description}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Offer"},
                            "url": offer_url,
                            "style": "primary"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Review Offer"},
                            "url": review_url,
                            "style": "danger"
                        }
                    ]
                }
            ]
        }

        await self.send_rich_message(payload)
