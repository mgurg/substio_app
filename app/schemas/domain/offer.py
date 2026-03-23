from datetime import date as dt_date, datetime as dt_datetime, time as dt_time
from decimal import Decimal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, EmailStr, Field, model_validator

from app.database.models.enums import OfferStatus, SourceType
from app.schemas.domain.common import BaseResponse, Coordinates
from app.schemas.domain.place import LegalRoleIndexResponse


class FacebookPost(BaseModel):
    user_name: str = Field(validation_alias=AliasChoices("user_name", "User Name"))
    post_content: str = Field(validation_alias=AliasChoices("post_content", "Post Content"))
    user_profile_url: str = Field(validation_alias=AliasChoices("user_profile_url", "User Profile URL"))
    post_url: str = Field(validation_alias=AliasChoices("post_url", "Post URL"))
    date_posted: str | None = Field(None, validation_alias=AliasChoices("date_posted", "Date Posted"))


class OfferRawAdd(BaseModel):
    raw_data: str
    author: str
    author_uid: str
    offer_uid: str
    timestamp: dt_datetime
    source: SourceType


class OfferAdd(BaseModel):
    author: str
    facility_uuid: UUID | None = None
    city_uuid: UUID | None = None
    roles: list[UUID] | None = None
    date: str | None = None
    hour: str | None = None
    price: float | None = None
    description: str | None = None
    invoice: bool | None = False
    submit_email: bool | None = False
    status: OfferStatus | None = None
    source: SourceType | None = None
    email: EmailStr | None = None

    @model_validator(mode="after")
    def check_location(self) -> "OfferAdd":
        if not self.facility_uuid and not self.city_uuid:
            raise ValueError("Either city_uuid or facility_uuid must be provided")
        return self


class OfferUpdate(BaseModel):
    author: str | None = None
    facility_uuid: UUID | None = None
    city_uuid: UUID | None = None
    roles: list[UUID] | None = None
    date: str | None = None
    hour: str | None = None
    price: float | None = None
    description: str | None = None
    invoice: bool | None = None
    submit_email: bool | None = False
    status: OfferStatus | None = None
    email: EmailStr | None = None

    @model_validator(mode="after")
    def check_location(self) -> "OfferUpdate":
        if "facility_uuid" in self.model_fields_set or "city_uuid" in self.model_fields_set:
            if not self.facility_uuid and not self.city_uuid:
                raise ValueError("Either city_uuid or facility_uuid must be provided")
        return self


class OfferIndexResponse(BaseResponse):
    uuid: UUID
    author: str
    place_name: str | None = None
    city_name: str | None = None
    city_uuid: UUID | int | None = Field(None, validation_alias=AliasChoices("city_uuid", "city_id"))
    facility_uuid: UUID | int | None = Field(None, validation_alias=AliasChoices("facility_uuid", "place_id"))
    date: dt_date | None = None
    hour: dt_time | None = None
    price: Decimal | None = None
    description: str | None = None
    invoice: bool | None = None
    status: OfferStatus
    added_at: dt_datetime | None = None
    valid_to: dt_datetime | None = None
    legal_roles: list[LegalRoleIndexResponse] = []

    @model_validator(mode="before")
    @classmethod
    def map_relations(cls, data):
        if hasattr(data, "city") and data.city:
            data.city_uuid = data.city.uuid
        if hasattr(data, "place") and data.place:
            data.facility_uuid = data.place.uuid
        return data


class OfferMapResponse(BaseResponse):
    uuid: UUID
    coordinates: Coordinates | None = None


class OfferEmail(BaseResponse):
    email: EmailStr


class OffersCount(BaseResponse):
    count: int


class OffersPaginated(BaseResponse):
    data: list[OfferIndexResponse]
    count: int
    offset: int
    limit: int


class RawOfferIndexResponse(BaseResponse):
    uuid: UUID
    author: str
    author_uid: str | None = None
    email: str | None = None
    raw_data: str | None = None
    offer_uid: str | None = None
    added_at: dt_datetime | None = None
    status: OfferStatus
    source: SourceType | None = None
    visible: bool | None = None
    url: str | None = None
    description: str | None = None
    price: Decimal | None = None
    hour: dt_time | None = None
    date: dt_date | None = None
    city_name: str | None = None
    place_name: str | None = None


class RawOffersPaginated(BaseResponse):
    data: list[RawOfferIndexResponse]
    count: int
    offset: int
    limit: int


class SimilarOfferIndexResponse(BaseResponse):
    uuid: UUID
    author: str


class ImportResult(BaseModel):
    total_records: int
    imported_records: int
    skipped_records: int
    errors: list[str]

    @property
    def success(self) -> bool:
        return True

    @property
    def count(self) -> int:
        return self.imported_records
