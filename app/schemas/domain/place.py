from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.database.models.enums import PlaceCategory
from app.schemas.domain.common import BaseResponse, CoordinateRange, Coordinates
from app.utils.validators import round_to_7_decimal_places


class Address(BaseModel):
    street: str | None = None
    street_name: str | None = None
    street_number: str | None = None
    postal_code: str | None = None
    city: str | None = None


class PlaceAdd(BaseModel):
    category: PlaceCategory
    type: str | None = None
    name: str
    department: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: Address | None = None
    coordinates: Coordinates | None = None


class CityAdd(BaseModel):
    city_name: str
    coordinates: Coordinates
    range: CoordinateRange | None = None
    population: int | None = None
    importance: float | None = None
    category: str
    state: str | None = None
    voivodeship_name: str
    voivodeship_iso: str
    teryt_simc: str


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
