import datetime as dt
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.database.models.enums import OfferStatus, PlaceCategory, SourceType


class BaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StandardResponse(BaseResponse):
    ok: bool


class LegalRoleIndexResponse(BaseResponse):
    uuid: UUID
    name: str


class RolesResponse(BaseResponse):
    uuid: UUID
    name: str


class PlaceResponse(BaseResponse):
    uuid: UUID
    name: str
    lat: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]
    lon: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]


class CityResponse(BaseResponse):
    uuid: UUID
    name: str
    lat: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]
    lon: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]


class OfferIndexResponse(BaseResponse):
    uuid: UUID
    author: str
    place_name: str
    description: str
    email: EmailStr | None
    url: str | None
    place: PlaceResponse | None = None
    city: CityResponse | None = None
    legal_roles: list[RolesResponse]
    date: dt.date | None = None
    hour: dt.time | None = None
    valid_to: dt.datetime | None = None


class RawOfferIndexResponse(BaseResponse):
    uuid: UUID
    author: str
    author_uid: str | None = None
    offer_uid: str
    raw_data: str | None = None
    source: SourceType
    author: str | None = None
    description: str | None = None
    email: EmailStr | None
    url: str | None
    invoice: bool | None = None
    place: PlaceResponse | None = None
    city: CityResponse | None = None
    place_name: str | None = None
    legal_roles: list[RolesResponse]
    date: dt.date | None = None
    hour: dt.time | None = None
    status: OfferStatus | None = None
    added_at: dt.datetime


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
    voivodeship_name: str


class ImportResult(BaseModel):
    total_records: int
    imported_records: int
    skipped_records: int
    errors: list[str]
