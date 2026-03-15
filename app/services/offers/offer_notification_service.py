from uuid import UUID

from loguru import logger

from app.database.models.enums import SourceType
from app.database.models.models import Offer
from app.infrastructure.notifications.email.email_notifier_base import EmailNotifierBase
from app.infrastructure.notifications.slack.slack_notifier_base import SlackNotifierBase


class OfferNotificationService:
    def __init__(
        self,
        slack_notifier: SlackNotifierBase,
        email_notifier: EmailNotifierBase,
    ) -> None:
        self.slack_notifier = slack_notifier
        self.email_notifier = email_notifier

    async def notify_new_offer_slack(self, offer_add, offer_uuid: str) -> None:
        if offer_add.source != SourceType.BOT:
            await self.slack_notifier.send_new_offer_notification(
                author=offer_add.author,
                email=offer_add.email,
                description=offer_add.description,
                offer_uuid=offer_uuid
            )

    async def send_offer_imported_email(self, offer: Offer, offer_uuid: str | UUID) -> None:
        """Send email notification for imported offer"""
        recipient_email = offer.email
        recipient_name = offer.author or "User"
        offer_uuid_str = str(offer_uuid)

        success = await self.email_notifier.send_offer_imported_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            offer_uuid=offer_uuid_str
        )

        if success:
            logger.info(f"Email notification sent successfully to {recipient_email} for offer {offer_uuid_str}")
        else:
            logger.warning(f"Failed to send email notification for offer {offer_uuid_str}")
