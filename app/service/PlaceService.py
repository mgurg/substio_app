from typing import Annotated, Sequence
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException
from loguru import logger
from starlette.status import (
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from app.common.text_utils import sanitize_name
from app.database.models.models import Place, City
from app.database.repository.CityRepo import CityRepo
from app.database.repository.PlaceRepo import PlaceRepo
from app.schemas.rest.requests import PlaceAdd, CityAdd


class PlaceService:
    def __init__(
            self,
            city_repo: Annotated[CityRepo, Depends()],
            place_repo: Annotated[PlaceRepo, Depends()]
    ) -> None:
        self.city_repo = city_repo
        self.place_repo = place_repo

    async def get_place_by_uuid(self, place_uuid: UUID) -> Place | None:
        db_item = await self.place_repo.get_by_uuid(place_uuid)

        if not db_item:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Place `{place_uuid}` not found!")

        return db_item

    async def create(self, place_add: PlaceAdd) -> None:
        db_place = await self.place_repo.get_by_name_and_street(place_add.name, place_add.street)
        if db_place:
            logger.warning(f"Place `{place_add.name}` already exists as {db_place.uuid}")
            raise HTTPException(status_code=HTTP_409_CONFLICT, detail=f"Place `{place_add.name}` already exists")

        place = {
            "uuid": str(uuid4()),
            "type": place_add.type,
            "name": place_add.name,
            "name_ascii": sanitize_name(place_add.name),
            "category": place_add.category,
            "street_name": place_add.street,
            "postal_code": place_add.postal_code,
            "city": place_add.city,
            "lat": place_add.lat,
            "lon": place_add.lon
        }

        await self.place_repo.create(**place)

        return None

    async def create_city(self, city: CityAdd) -> None:
        db_city = await self.city_repo.get_by_name(city.city_name)
        if db_city:
            logger.warning(f"City `{city.name}` already exists as {db_city.uuid}")
            raise HTTPException(status_code=HTTP_409_CONFLICT, detail=f"City `{city.name}` already exists")

        city_data = {
            "uuid": str(uuid4()),
            "name": city.city_name,
            "name_ascii": sanitize_name(city.city_name),
            "lat": city.lat,
            "lon": city.lon,
            "lat_min": city.lat_min,
            "lat_max": city.lat_max,
            "lon_min": city.lon_min,
            "lon_max": city.lon_max,
            "population": city.population,
            "importance": city.importance,
            "category": city.category,
            "region": city.state
        }

        await self.city_repo.create(**city_data)

        return None

    async def get_cities(self, city_name: str) -> Sequence[City]:
        sanitized_name = sanitize_name(city_name)
        return await self.city_repo.get_by_partial_name(sanitized_name)

    async def get_facilities(self, city_name: str) -> Sequence[Place]:
        sanitized_name = sanitize_name(city_name)
        return await self.place_repo.get_by_partial_name(sanitized_name)