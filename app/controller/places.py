from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import get_place_service
from app.database.models.models import City, Place
from app.schemas.domain.place import CityAdd, CityIndexResponse, PlaceAdd, PlaceIndexResponse
from app.services.place_service import PlaceService

place_router = APIRouter()

# CurrentUser = Annotated[User, Depends(check_token)]
placeServiceDependency = Annotated[PlaceService, Depends(get_place_service)]


@place_router.post("/")
async def create_place(place_service: placeServiceDependency, place_add: PlaceAdd):
    await place_service.create(place_add)

    return None


@place_router.post("/city")
async def create_city(place_service: placeServiceDependency, city: CityAdd):
    await place_service.create_city(city)

    return None


@place_router.get("/facility/{place_name}", response_model=list[PlaceIndexResponse])
async def get_facilities(
    place_service: placeServiceDependency,
    place_name: str,
    place_type: str | None = None,
) -> Sequence[Place]:
    return await place_service.get_facilities(place_name, place_type)


@place_router.get("/facility/uuid/{place_uuid}", response_model=PlaceIndexResponse)
async def get_facility(place_service: placeServiceDependency, place_uuid: UUID) -> Place:
    return await place_service.get_place_by_uuid(place_uuid)


@place_router.get("/city/uuid/{city_uuid}", response_model=CityIndexResponse)
async def get_city(place_service: placeServiceDependency, city_uuid: UUID) -> City:
    return await place_service.get_city_by_uuid(city_uuid)


@place_router.get("/city/{city_name}", response_model=list[CityIndexResponse])
async def get_cities(place_service: placeServiceDependency, city_name: str) -> Sequence[City]:
    return await place_service.get_cities(city_name)
