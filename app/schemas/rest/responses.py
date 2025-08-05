from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.database.models.enums import PlaceCategory, SourceType


class BaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StandardResponse(BaseResponse):
    ok: bool

class LegalRoleIndexResponse(BaseResponse):
    uuid: UUID
    name: str

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


class PlaceIndexResponse(BaseResponse):
    uuid: UUID
    category: PlaceCategory
    name: str
    street_name: str | None = None
    postal_code: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    department: str | None = None
    lat: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]
    lon: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]
    website: str | None = None


class CityIndexResponse(BaseResponse):
    uuid: UUID
    name: str | None = None
    lat: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]
    lon: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]
    # lat_min: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)] | None = None  # South Latitude
    # lat_max: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)] | None = None  # North Latitude
    # lon_min: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)] | None = None  # West Longitude
    # lon_max: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)] | None = None  # East Longitude
    # importance: float | None
    # state: str | None
