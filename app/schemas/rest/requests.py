from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.database.models.enums import OfferStatus, PlaceCategory, SourceType
from app.schemas.validators.validators import round_to_7_decimal_places


class OfferAdd(BaseModel):
    raw_data: str
    author: str
    author_uid: str
    offer_uid: str
    timestamp: datetime
    source: SourceType


class OfferUpdate(BaseModel):
    facility_uuid: UUID | None = None
    facility_name: str | None = None
    city_uuid: UUID | None = None
    city_name: str | None = None
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
    roles: list[UUID] | None = None


class PlaceAdd(BaseModel):
    category: PlaceCategory
    type: str | None = None
    name: str | None = None
    street: str | None = None
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
    lat: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]
    lon: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]
    lat_min: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]  # South Latitude
    lat_max: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]  # North Latitude
    lon_min: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]  # West Longitude
    lon_max: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)]  # East Longitude
    population: int | None
    importance: float | None
    category: str
    state: str | None

    @field_validator("lat", "lon", "lat_min", "lat_max", "lon_min", "lon_max", mode="before")
    @classmethod
    def sanitize_coordinates(cls, v):
        return round_to_7_decimal_places(v)
