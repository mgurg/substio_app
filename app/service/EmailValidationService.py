from loguru import logger

from app.config import get_settings
from app.database.models.enums import OfferStatus, SourceType
from app.database.models.models import Offer

settings = get_settings()


class EmailValidationService:
    """Service for validating email sending conditions"""

    @staticmethod
    def should_send_offer_email(
        updated_offer: Offer,
        original_offer: Offer,
        submit_email: bool
    ) -> bool:
        """
        Determine if an offer email should be sent based on multiple conditions.

        Args:
            updated_offer: The offer after updates
            original_offer: The offer before updates (for checking source)
            submit_email: Whether the user explicitly requested email sending

        Returns:
            bool: True if email should be sent, False otherwise
        """
        if not updated_offer.email:
            logger.info("Skipping email sending: no email set on offer")
            return False

        if settings.APP_ENV != "PROD":
            logger.info("Skipping email sending: not running in PROD")
            return False

        if not submit_email:
            logger.info("Skipping email sending: submit_email is False")
            return False

        if updated_offer.status != OfferStatus.ACTIVE:
            logger.info(f"Skipping email sending: offer status is {updated_offer.status}")
            return False

        if original_offer.source != SourceType.BOT:
            logger.info(f"Skipping email sending: source is {original_offer.source}")
            return False

        return True
