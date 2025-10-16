from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.database.models.models import City
from app.database.repository.CityRepo import CityRepo


class CityService:
    def __init__(
            self,
            city_repo: Annotated[CityRepo, Depends()]
    ) -> None:
        self.city_repo = city_repo

    async def get_city_by_uuid(self, city_uuid: UUID) -> City:
        return await self.city_repo.get_by_uuid(city_uuid)
