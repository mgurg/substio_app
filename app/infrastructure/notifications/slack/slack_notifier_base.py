from abc import ABC, abstractmethod

from pydantic import EmailStr


class SlackNotifierBase(ABC):
    @abstractmethod
    async def send_message(self, text: str) -> None:
        pass

    @abstractmethod
    async def send_rich_message(self, payload: dict) -> None:
        pass

    def _format_offer_url(self, offer_uuid: str) -> str:
        raise NotImplementedError

    def _format_review_url(self, offer_uuid: str) -> str:
        raise NotImplementedError

    async def send_new_offer_notification(self, author: str, email: EmailStr, description: str, offer_uuid: str) -> None:
        """Send a formatted notification for a new offer."""
        offer_url = self._format_offer_url(offer_uuid)
        review_url = self._format_review_url(offer_uuid)

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
        offer_url = self._format_offer_url(offer_uuid)
        review_url = self._format_review_url(offer_uuid)

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
