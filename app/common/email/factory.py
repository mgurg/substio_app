from functools import lru_cache

from app.common.email.EmailNotifierBase import EmailNotifierBase
from app.common.email.MailerSendNotifier import MailerSendNotifier


@lru_cache
def get_email_notifier() -> EmailNotifierBase:
    """
    Factory function to get email notifier instance.
    Can be extended to support different email providers based on config.
    """
    return MailerSendNotifier()
