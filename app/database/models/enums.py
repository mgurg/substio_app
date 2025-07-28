from enum import Enum


class SourceType(Enum):
    BOT = "bot"
    USER = "user"


class OfferStatus(Enum):
    NEW = "new"
    DRAFT = "draft"
    PROCESSED = "processed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ACTIVE = "active"
