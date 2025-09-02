import re
from collections.abc import Sequence
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException
from loguru import logger
from starlette.status import (
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from app.common.text_utils import sanitize_name
from app.database.models.models import City, Place
from app.database.repository.CityRepo import CityRepo
from app.database.repository.PlaceRepo import PlaceRepo
from app.schemas.rest.requests import CityAdd, PlaceAdd


class PlaceService:
    def __init__(
            self,
            city_repo: Annotated[CityRepo, Depends()],
            place_repo: Annotated[PlaceRepo, Depends()]
    ) -> None:
        self.city_repo = city_repo
        self.place_repo = place_repo

    async def get_place_by_uuid(self, place_uuid: UUID) -> Place | None:
        db_place = await self.place_repo.get_by_uuid(place_uuid)

        if not db_place:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Place `{place_uuid}` not found!")

        return db_place

    async def get_city_by_uuid(self, city_uuid: UUID) -> Place | None:
        db_city = await self.city_repo.get_by_uuid(city_uuid)

        if not db_city:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"City `{city_uuid}` not found!")

        return db_city

    async def create(self, place_add: PlaceAdd) -> None:
        lat = float(place_add.lat) if place_add.lat is not None else None
        lon = float(place_add.lon) if place_add.lon is not None else None

        if lat is None or lon is None:
            raise ValueError("Latitude and longitude are required for distance calculation")

        db_place = await self.place_repo.get_by_name_and_distance(place_add.name, lat, lon, 1)

        if db_place:
            uuids = ", ".join(str(p.uuid) for p in db_place)  # Log all UUIDs of conflicting places
            logger.warning(f"Place `{place_add.name}` already exists as {uuids}")
            # raise HTTPException(status_code=HTTP_409_CONFLICT, detail=f"Place `{place_add.name}` already exists" )

        place = {
            "uuid": str(uuid4()),
            "type": place_add.type,
            "name": place_add.name,
            "street_name": place_add.street_name,
            "street_number": place_add.street_number,
            "department": place_add.department,
            "name_ascii": sanitize_name(place_add.name),
            "category": place_add.category,
            "postal_code": place_add.postal_code,
            "city": place_add.city,
            "lat": place_add.lat,
            "lon": place_add.lon
        }

        if not place_add.street_name and place_add.street:
            street_name, street_number = self.split_street(place_add.street)

            place["street_name"] = street_name
            place["street_number"] = street_number
        if place_add.street_name and not place_add.street_number:
            place["street_name"] = place_add.street_name
            place["street_number"] = place_add.street_number

        await self.place_repo.create(**place)

        return None

    def split_street(self, street: str):
        """
        Splits a street string into (street_name, street_number).
        Handles Polish-style house numbers with letters, slashes, commas, and ranges.
        Normalizes street_number (removes internal spaces).
        """
        pattern = (
            r'\s('
            r'\d+\s*[A-Za-z]?'  # 22, 4d, 18 a
            r'(?:[-/]\d+\s*[A-Za-z]?)*'  # -13, /25, /2a, -13B
            r'(?:,\s*\d+\s*[A-Za-z]?(?:[-/]\d+\s*[A-Za-z]?)*?)*'  # , 23, , 25a/2, , 12-13
            r')$'
        )

        match = re.search(pattern, street)
        if match:
            street_number = re.sub(r'\s+', '', match.group(1))  # normalize: remove spaces
            street_name = street[:match.start(1)].strip()
        else:
            street_name = street.strip()
            street_number = None
        return street_name, street_number

    async def create_city(self, city: CityAdd) -> None:
        db_city = await self.city_repo.get_by_teryt(city.teryt_simc)
        if db_city:
            logger.warning(f"City `{city.city_name} - {city.teryt_simc}` already exists as {db_city.uuid}")
            raise HTTPException(status_code=HTTP_409_CONFLICT,
                                detail=f"City `{city.city_name} - {city.state}` already exists as {db_city.uuid}")

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
            "voivodeship_name": city.voivodeship_name,
            "voivodeship_iso": city.voivodeship_iso,
            "teryt_simc": city.teryt_simc if city.teryt_simc else None,
        }

        await self.city_repo.create(**city_data)

        return None

    async def get_cities(self, city_name: str) -> Sequence[City]:
        sanitized_name = sanitize_name(city_name)
        return await self.city_repo.get_by_partial_name(sanitized_name)

    async def get_facilities(self, city_name: str, place_type: str | None = None) -> Sequence[Place]:
        sanitized_name = sanitize_name(city_name)
        return await self.place_repo.get_by_partial_name(sanitized_name, place_type)
