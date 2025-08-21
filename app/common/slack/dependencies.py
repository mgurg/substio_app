
from app.config import get_settings
from app.common.slack.SlackNotifier import SlackNotifier
from app.common.slack.SlackNotifierBase import SlackNotifierBase


# ------------------------------
# Dependency for FastAPI DI
# ------------------------------
def get_slack_notifier() -> SlackNotifierBase:
    settings = get_settings()
    return SlackNotifier(webhook_url=settings.SLACK_WEBHOOK_URL)
