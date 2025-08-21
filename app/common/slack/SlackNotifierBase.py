from abc import ABC, abstractmethod


class SlackNotifierBase(ABC):
    @abstractmethod
    async def send_message(self, text: str) -> None:
        pass
