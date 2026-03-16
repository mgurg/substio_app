from functools import lru_cache

from app.infrastructure.notifications.email.email_notifier_base import EmailNotifierBase
from app.infrastructure.notifications.email.mailer_send_notifier import MailerSendNotifier


@lru_cache
def get_email_notifier() -> EmailNotifierBase:
    """
    Factory function to get email notifier instance.
    Can be extended to support different email providers based on config.
    """
    return MailerSendNotifier()
