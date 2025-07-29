from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.database.models.enums import SourceType


class BaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StandardResponse(BaseResponse):
    ok: bool


class OfferIndexResponse(BaseResponse):
    uuid: UUID


class RawOfferIndexResponse(BaseResponse):
    uuid: UUID
    author: str
    author_uid: str
    offer_uid: str
    raw_data: str
    source: SourceType
    added_at: datetime


class OffersPaginated(BaseResponse):
    data: list[OfferIndexResponse]
    count: int
    limit: int
    offset: int


class RawOffersPaginated(BaseResponse):
    data: list[RawOfferIndexResponse]
    count: int
    limit: int
    offset: int
