
from app.common.slack.SlackNotifier import SlackNotifier
from app.common.slack.SlackNotifierBase import SlackNotifierBase


# ------------------------------
# Dependency for FastAPI DI
# ------------------------------
def get_slack_notifier() -> SlackNotifierBase:
    return SlackNotifier()
