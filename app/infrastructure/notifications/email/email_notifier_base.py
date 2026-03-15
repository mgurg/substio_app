from abc import ABC, abstractmethod
from typing import Any


class EmailNotifierBase(ABC):
    """Base class for email notification services"""

    @abstractmethod
    async def send_offer_imported_email(
            self,
            recipient_email: str,
            recipient_name: str,
            offer_uuid: str,
            **kwargs
    ) -> bool:
        """
        Send an email notification when an offer is imported.

        Args:
            recipient_email: Email address of the recipient
            recipient_name: Name of the recipient
            offer_uuid: UUID of the offer
            **kwargs: Additional template variables

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        pass

    @abstractmethod
    async def send_custom_email(
            self,
            recipient_email: str,
            recipient_name: str,
            subject: str,
            template_id: str,
            template_vars: dict[str, Any]
    ) -> bool:
        """
        Send a custom email with specified template.

        Args:
            recipient_email: Email address of the recipient
            recipient_name: Name of the recipient
            subject: Email subject
            template_id: Template identifier
            template_vars: Variables for template personalization

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        pass
