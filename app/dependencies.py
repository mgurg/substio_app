from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.database.repository.CityRepo import CityRepo
from app.database.repository.PlaceRepo import PlaceRepo
from app.service.PlaceService import PlaceService


def get_city_repo(session: AsyncSession = Depends(get_db)) -> CityRepo:
    return CityRepo(session)


def get_place_repo(session: AsyncSession = Depends(get_db)) -> PlaceRepo:
    return PlaceRepo(session)


def get_place_service(
        city_repo: CityRepo = Depends(get_city_repo),
        place_repo: PlaceRepo = Depends(get_place_repo),
) -> PlaceService:
    return PlaceService(city_repo=city_repo, place_repo=place_repo)
