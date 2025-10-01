from pydantic import EmailStr

from app.common.slack.SlackNotifierBase import SlackNotifierBase


class FakeSlackNotifier(SlackNotifierBase):
    def __init__(self):
        self.sent_messages: list[str] = []
        self.sent_payloads: list[dict] = []

    async def send_message(self, text: str) -> None:
        self.sent_messages.append(text)

    async def send_rich_message(self, payload: dict) -> None:
        self.sent_payloads.append(payload)

    async def send_new_offer_rich_notification(self, author: str, email: EmailStr, description: str, offer_uuid: str) -> None:
        offer_url = f"http://localhost:3000/raw/{offer_uuid}"
        review_url = f"http://localhost:3000/substytucje-procesowe/review-{offer_uuid}"

        payload = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f":tada: *New offer created!* \n\n"
                            f"*Author:* {author}\n"
                            f"*Email:* {email}\n"
                            f"*Description:* {description}"
                        ),
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Offer"},
                            "url": offer_url,
                            "style": "primary",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Review Offer"},
                            "url": review_url,
                            "style": "danger",
                        },
                    ],
                },
            ]
        }

        await self.send_rich_message(payload)

    async def send_new_offer_notification(self, author: str, email: EmailStr, description: str, offer_uuid: str) -> None:
        # Build the same message format for testing consistency
        offer_url = f"http://localhost:3000/raw/{offer_uuid}"  # or use settings if needed
        review_url = f"http://localhost:3000/substytucje-procesowe/review-{offer_uuid}"

        message = (
            f":tada: New offer created by *{author}* \n"
            f"email: {email}\n"
            f"description: {description}.\n"
            f"<{offer_url}|View Offer>\n"
            f"<{review_url}|Review Offer>"
        )

        await self.send_message(message)
