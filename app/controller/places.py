from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.service.PlaceService import PlaceService

place_router = APIRouter()

# CurrentUser = Annotated[User, Depends(check_token)]
placeServiceDependency = Annotated[PlaceService, Depends()]


@place_router.get("/{place_uuid}")
async def item_get_one(place_service: placeServiceDependency, place_uuid: UUID):
    db_item = await place_service.get_place_by_uuid(place_uuid)

    return db_item
