from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from starlette.status import (
    HTTP_404_NOT_FOUND,
)

from app.database.models.models import Place
from app.database.repository.PlaceRepo import PlaceRepo


class PlaceService:
    def __init__(
            self,
            place_repo: Annotated[PlaceRepo, Depends()]
    ) -> None:
        self.place_repo = place_repo

    async def get_place_by_uuid(self, place_uuid: UUID) -> Place | None:
        db_item = await self.place_repo.get_by_uuid(place_uuid)

        if not db_item:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Place `{place_uuid}` not found!")

        return db_item
