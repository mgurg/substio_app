from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.database.models.enums import SourceType, OfferStatus


class OfferAdd(BaseModel):
    raw_data: str
    author: str
    author_uid: str
    offer_uid: str
    timestamp: datetime
    source: SourceType


class OfferUpdate(BaseModel):
    place_uuid: UUID | None = None
    place_name: str | None = None
    email: EmailStr | None = None
    url: str | None = None
    date: str | None = None
    hour: str | None = None
    price: float | None = None
    description: str | None = None
    invoice: bool | None = None
    visible: bool | None = None
    status: OfferStatus | None = None
    legal_roles: list[str] | None = None