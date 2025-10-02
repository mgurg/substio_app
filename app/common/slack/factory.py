from app.common.slack.SlackNotifier import SlackNotifier
from app.common.slack.SlackNotifierBase import SlackNotifierBase


def get_slack_notifier() -> SlackNotifierBase:
    return SlackNotifier()
