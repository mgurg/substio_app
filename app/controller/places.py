from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import get_place_service
from app.schemas.rest.requests import CityAdd, PlaceAdd
from app.schemas.rest.responses import CityIndexResponse, PlaceIndexResponse
from app.service.PlaceService import PlaceService

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


@place_router.get("/facility/{place_name}")
async def get_facilities(place_service: placeServiceDependency, place_name: str, place_type: str | None = None,
                         ) -> list[PlaceIndexResponse]:
    return await place_service.get_facilities(place_name, place_type)


@place_router.get("/facility/uuid/{place_uuid}")
async def get_facility(place_service: placeServiceDependency, place_uuid: UUID) -> PlaceIndexResponse:
    return await place_service.get_place_by_uuid(place_uuid)


@place_router.get("/city/uuid/{city_uuid}")
async def get_city(place_service: placeServiceDependency, city_uuid: UUID) -> CityIndexResponse:
    return await place_service.get_city_by_uuid(city_uuid)


@place_router.get("/city/{city_name}")
async def get_cities(place_service: placeServiceDependency, city_name: str) -> list[
    CityIndexResponse]:
    return await place_service.get_cities(city_name)
