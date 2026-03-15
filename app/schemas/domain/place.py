from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.database.models.enums import PlaceCategory
from app.schemas.domain.common import BaseResponse, Coordinates
from app.utils.validators import round_to_7_decimal_places


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
    website: str | None = None
    coordinates: Coordinates | None = None


class CityAdd(BaseModel):
    city_name: str
    coordinates: Coordinates
    lat_min: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)] | None = None
    lat_max: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)] | None = None
    lon_min: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)] | None = None
    lon_max: Annotated[Decimal | None, Field(max_digits=10, decimal_places=7)] | None = None
    population: int | None = None
    importance: float | None = None
    category: str
    state: str | None = None
    voivodeship_name: str
    voivodeship_iso: str
    teryt_simc: str

    @field_validator("lat_min", "lat_max", "lon_min", "lon_max", mode="before")
    @classmethod
    def sanitize_coordinates(cls, v):
        return round_to_7_decimal_places(v)


class PlaceIndexResponse(BaseResponse):
    uuid: UUID
    name: str
    category: PlaceCategory


class CityIndexResponse(BaseResponse):
    uuid: UUID
    name: str
    coordinates: Coordinates | None = None
    voivodeship_name: str | None = None


class LegalRoleIndexResponse(BaseResponse):
    uuid: UUID
    name: str
