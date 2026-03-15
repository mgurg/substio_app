from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.validators import round_to_7_decimal_places


class Coordinates(BaseModel):
    lat: Annotated[Decimal, Field(ge=-90, le=90, max_digits=10, decimal_places=7)]
    lon: Annotated[Decimal, Field(ge=-180, le=180, max_digits=10, decimal_places=7)]

    @field_validator("lat", "lon", mode="before")
    @classmethod
    def sanitize_coordinates(cls, v):
        return round_to_7_decimal_places(v)


class CoordinateRange(BaseModel):
    lat_min: Annotated[Decimal | None, Field(ge=-90, le=90, max_digits=10, decimal_places=7)] = None
    lat_max: Annotated[Decimal | None, Field(ge=-90, le=90, max_digits=10, decimal_places=7)] = None
    lon_min: Annotated[Decimal | None, Field(ge=-180, le=180, max_digits=10, decimal_places=7)] = None
    lon_max: Annotated[Decimal | None, Field(ge=-180, le=180, max_digits=10, decimal_places=7)] = None

    @field_validator("lat_min", "lat_max", "lon_min", "lon_max", mode="before")
    @classmethod
    def sanitize_coordinates(cls, v):
        return round_to_7_decimal_places(v)


class HealthCheck(BaseModel):
    status: str = "OK"


class BaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
