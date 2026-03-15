from abc import ABC, abstractmethod

from pydantic import EmailStr


class SlackNotifierBase(ABC):
    @abstractmethod
    async def send_message(self, text: str) -> None:
        pass

    @abstractmethod
    async def send_rich_message(self, text: str) -> None:
        pass

    @abstractmethod
    async def send_new_offer_notification(self, author: str, email: EmailStr, description: str,
                                          offer_uuid: str) -> None:
        pass

    @abstractmethod
    async def send_new_offer_rich_notification(self, author: str, email: EmailStr, description: str,
                                                offer_uuid: str) -> None:
        pass
