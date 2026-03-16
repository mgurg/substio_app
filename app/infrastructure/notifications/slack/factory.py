from app.infrastructure.notifications.slack.slack_notifier import SlackNotifier
from app.infrastructure.notifications.slack.slack_notifier_base import SlackNotifierBase


def get_slack_notifier() -> SlackNotifierBase:
    return SlackNotifier()
