from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from starlette.status import (
    HTTP_404_NOT_FOUND,
)

from app.models.models import City
from app.repository.CityRepo import CityRepo


class CityService:
    def __init__(
            self,
            city_repo: Annotated[CityRepo, Depends()]
    ) -> None:
        self.city_repo = city_repo

    async def get_city_by_uuid(self, city_uuid: UUID) -> City | None:
        db_item = await self.city_repo.get_by_uuid(city_uuid)

        if not db_item:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"City `{city_uuid}` not found!")

        return db_item
