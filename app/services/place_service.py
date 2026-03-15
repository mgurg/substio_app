import re
from collections.abc import Sequence
from uuid import UUID, uuid4

from loguru import logger

from app.common.text_utils import sanitize_name
from app.database.models.models import City, Place
from app.core.protocols import CityRepoProtocol, PlaceRepoProtocol
from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.domain.place import CityAdd, PlaceAdd
from app.services.places.city_mapper import CityMapper
from app.services.places.place_mapper import PlaceMapper


class PlaceService:
    def __init__(
        self,
        city_repo: CityRepoProtocol,
        place_repo: PlaceRepoProtocol,
    ) -> None:
        self.city_repo = city_repo
        self.place_repo = place_repo

    async def get_place_by_uuid(self, place_uuid: UUID) -> Place | None:
        db_place = await self.place_repo.get_by_uuid(place_uuid)
        if not db_place:
            raise NotFoundError("Place", str(place_uuid))

        return db_place

    async def get_city_by_uuid(self, city_uuid: UUID) -> City:
        return await self.city_repo.get_by_uuid(city_uuid)

    async def create(self, place_add: PlaceAdd) -> None:
        lat = float(place_add.lat) if place_add.lat is not None else None
        lon = float(place_add.lon) if place_add.lon is not None else None

        if lat is None or lon is None:
            raise ValueError("Latitude and longitude are required for distance calculation")

        db_place = await self.place_repo.get_by_name_and_distance(place_add.name, lat, lon, 1)

        if db_place:
            uuids = ", ".join(str(p.uuid) for p in db_place)  # Log all UUIDs of conflicting places
            logger.warning(f"Place `{place_add.name}` already exists as {uuids}")
            raise ConflictError(f"Place `{place_add.name}` already exists")
            # raise HTTPException(status_code=HTTP_409_CONFLICT, detail=f"Place `{place_add.name}` already exists" )

        place_data = PlaceMapper.map_to_db_dict(place_add)
        await self.place_repo.create(**place_data)

        return None

    async def create_city(self, city: CityAdd) -> None:
        db_city = await self.city_repo.find_by_teryt(city.teryt_simc)
        if db_city:
            logger.warning(f"City `{city.city_name} - {city.teryt_simc}` already exists as {db_city.uuid}")
            raise ConflictError(f"City `{city.city_name} - {city.state}` already exists as {db_city.uuid}")

        city_data = CityMapper.map_to_db_dict(city)
        await self.city_repo.create(**city_data)

        return None

    async def get_cities(self, city_name: str) -> Sequence[City]:
        sanitized_name = sanitize_name(city_name)
        return await self.city_repo.get_by_partial_name(sanitized_name)

    async def get_facilities(self, city_name: str, place_type: str | None = None) -> Sequence[Place]:
        sanitized_name = sanitize_name(city_name)
        return await self.place_repo.get_by_partial_name(sanitized_name, place_type)
