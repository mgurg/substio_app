from app.common.slack.SlackNotifierBase import SlackNotifierBase


class FakeSlackNotifier(SlackNotifierBase):
    def __init__(self):
        self.sent_messages: list[str] = []

    async def send_message(self, text: str) -> None:
        # Just store the message instead of sending it
        self.sent_messages.append(text)
