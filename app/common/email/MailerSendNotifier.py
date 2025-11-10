from random import randint
from typing import Any

from loguru import logger
from mailersend import EmailBuilder, MailerSendClient

from app.common.email.EmailNotifierBase import EmailNotifierBase
from app.config import get_settings

settings = get_settings()


class MailerSendNotifier(EmailNotifierBase):
    """MailerSend implementation of email notification service"""

    def __init__(self):
        # Lazy-init the MailerSend client to avoid requiring API key at import/instantiation time (helps tests)
        self.client = None
        self.from_email = settings.APP_ADMIN_MAIL
        self.from_name = settings.APP_DOMAIN
        self.bcc_email = settings.APP_ADMIN_MAIL

    async def send_offer_imported_email(
            self,
            recipient_email: str,
            recipient_name: str,
            offer_uuid: str,
            **kwargs
    ) -> bool:
        """Send offer imported notification email"""
        template_vars = {
            "offer_url": f"{settings.APP_URL}/substytucje-procesowe/review-{offer_uuid}",
            "website_name": settings.APP_DOMAIN,
            "support_email": settings.APP_ADMIN_MAIL,
            **kwargs
        }

        return await self.send_custom_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject="Substytucja - Twoje ogłoszenie zostało zaimportowane",
            template_id="3zxk54vy71x4jy6v",
            template_vars=template_vars
        )

    async def send_custom_email(
            self,
            recipient_email: str,
            recipient_name: str,
            subject: str,
            template_id: str,
            template_vars: dict[str, Any]
    ) -> bool:
        """Send custom email with specified template"""
        try:
            logger.info(f"Sending email to {recipient_email}")

            # Ensure client is initialized lazily to avoid requiring API key during tests/import
            if self.client is None:
                self.client = MailerSendClient(api_key=settings.API_KEY_MAILERSEND)

            builder = (
                EmailBuilder()
                .from_email(email=self.from_email, name=self.from_name)
                .to_many([{"email": recipient_email, "name": recipient_name}])
                .subject(subject)
                .template(template_id)
                .personalize_many([
                    {
                        "email": recipient_email,
                        "data": template_vars
                    }
                ])
            )

            if randint(1, 10) == 1:  # Add BCC with 10% probability
                if hasattr(builder, "bcc"):
                    logger.info(f"Adding BCC to {self.bcc_email}")
                    builder = builder.bcc(email=self.bcc_email)
                else:
                    logger.debug("Email builder has no 'bcc' method; skipping BCC")

            email = builder.build()

            logger.info("Sending email...")
            response = self.client.emails.send(email)
            logger.info(f"Email sent successfully to {recipient_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            return False
