from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import get_place_service
from app.schemas.rest.requests import CityAdd, PlaceAdd
from app.schemas.rest.responses import CityIndexResponse, PlaceIndexResponse
from app.service.PlaceService import PlaceService

place_router = APIRouter()

# CurrentUser = Annotated[User, Depends(check_token)]
# placeServiceDependency = Annotated[PlaceService, Depends()]


@place_router.post("/")
async def create_place(place_add: PlaceAdd, place_service: PlaceService = Depends(get_place_service)):
    await place_service.create(place_add)

    return None


@place_router.post("/city")
async def create_city(city: CityAdd, place_service: PlaceService = Depends(get_place_service)):
    await place_service.create_city(city)

    return None


@place_router.get("/facility/{place_name}")
async def get_facilities(place_name: str, place_type: str | None = None,
                         place_service: PlaceService = Depends(get_place_service)) -> list[PlaceIndexResponse]:
    return await place_service.get_facilities(place_name, place_type)


@place_router.get("/facility/uuid/{place_uuid}")
async def get_facility(place_uuid: UUID,
                       place_service: PlaceService = Depends(get_place_service)) -> PlaceIndexResponse:
    return await place_service.get_place_by_uuid(place_uuid)


@place_router.get("/city/uuid/{city_uuid}")
async def get_city(city_uuid: UUID, place_service: PlaceService = Depends(get_place_service)) -> CityIndexResponse:
    return await place_service.get_city_by_uuid(city_uuid)


@place_router.get("/city/{city_name}")
async def get_cities(city_name: str, place_service: PlaceService = Depends(get_place_service)) -> list[
    CityIndexResponse]:
    return await place_service.get_cities(city_name)
