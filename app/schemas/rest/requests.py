from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.database.models.enums import OfferStatus, PlaceCategory, SourceType
from app.schemas.validators.validators import round_to_7_decimal_places


class OfferRawAdd(BaseModel):
    raw_data: str
    author: str
    author_uid: str
    offer_uid: str
    timestamp: datetime
    source: SourceType


class OfferAdd(BaseModel):
    author: str
    facility_uuid: UUID | None = None
    facility_name: str | None = None
    city_uuid: UUID | None = None
    city_name: str | None = None
    place_name: str | None = None
    email: EmailStr
    date: str | None = None
    hour: str | None = None
    description: str | None = None
    invoice: bool | None = None
    status: OfferStatus | None = None
    roles: list[UUID] | None = None
    source: SourceType


class FacebookPost(BaseModel):
    user_name: str = Field(..., alias="User Name")
    user_profile_url: str = Field(..., alias="User Profile URL")
    post_url: str = Field(..., alias="Post URL")
    post_content: str = Field(..., alias="Post Content")
    date_posted: str | None = Field(None, alias="Date Posted")
    number_of_shares: int | None = Field(None, alias="Number of Shares")
    number_of_comments: int | None = Field(None, alias="Number of Comments")
    number_of_likes: int | None = Field(None, alias="Number of Likes")
    attachments: str | None = Field(None, alias="Attachments")
    group_url: str | None = Field(None, alias="Group URL")
    number_of_group_members: str | None = Field(
        None, alias="Number of Group Members"
    )

    model_config = {
        "populate_by_name": True,  # allows usage of both alias and pythonic names
        "str_strip_whitespace": True,
        "extra": "ignore",  # ignore unknown fields
    }


class OfferUpdate(BaseModel):
    facility_uuid: UUID | None = None
    facility_name: str | None = None
    city_uuid: UUID | None = None
    city_name: str | None = None
    place_name: str | None = None
    author: str | None = None
    email: EmailStr | None = None
    url: str | None = None
    date: str | None = None
    hour: str | None = None
    price: float | None = None
    description: str | None = None
    invoice: bool | None = None
    visible: bool | None = None
    status: OfferStatus | None = None
    roles: list[UUID] | None = None
    submit_email: bool | None = False


class PlaceAdd(BaseModel):
    category: PlaceCategory
    type: str | None = None
    name: str
    street: str | None = None
    street_name: str | None = None
    street_number: str | None = None
    postal_code: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    epuap: str | None = None
    department: str | None = None
    lat: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]
    lon: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]
    website: str | None = None

    @field_validator("lat", "lon", mode="before")
    @classmethod
    def sanitize_coordinates(cls, v):
        return round_to_7_decimal_places(v)


class CityAdd(BaseModel):
    city_name: str
    lat: Annotated[Decimal, Field(max_digits=10, decimal_places=7)]
    lon: Annotated[Decimal, Field(max_digits=10, decimal_places=7)]
    lat_min: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)] | None = None  # South Latitude
    lat_max: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)] | None = None  # North Latitude
    lon_min: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)] | None = None  # West Longitude
    lon_max: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)] | None = None  # East Longitude
    population: int | None = None
    importance: float | None = None
    category: str
    state: str | None = None
    voivodeship_name: str
    voivodeship_iso: str
    teryt_simc: str

    @field_validator("lat", "lon", "lat_min", "lat_max", "lon_min", "lon_max", mode="before")
    @classmethod
    def sanitize_coordinates(cls, v):
        return round_to_7_decimal_places(v)
