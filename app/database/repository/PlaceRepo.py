from collections.abc import Sequence
from typing import Annotated, Any, Coroutine, Sequence
from uuid import UUID

from fastapi import Depends
from sqlalchemy import and_, func, select, Row, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.database.models.models import Place
from app.database.repository.generics import GenericRepo

UserDB = Annotated[AsyncSession, Depends(get_db)]

EARTH_RADIUS_KM = 6371.0

class PlaceRepo(GenericRepo[Place]):
    def __init__(self, session: UserDB) -> None:
        self.Model = Place
        super().__init__(session, self.Model)

    async def get_by_uuid(self, uuid: UUID) -> Place | None:
        query = select(self.Model).where(self.Model.uuid == uuid)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_partial_name(self, name: str, facility_type: str | None = None) -> Sequence[Place]:
        conditions = [func.lower(self.Model.name_ascii).ilike(f"%{name.lower()}%")]

        if facility_type:
            conditions.append(self.Model.type == facility_type)

        query = select(self.Model).where(and_(*conditions)).limit(5)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_name_and_distance(self, name: str, lat: float, lon: float, min_distance_km: float = 1.0) -> Sequence[Place]:
        haversine = EARTH_RADIUS_KM * func.acos(
            func.cos(func.radians(lat)) *
            func.cos(func.radians(self.Model.lat)) *
            func.cos(func.radians(self.Model.lon) - func.radians(lon)) +
            func.sin(func.radians(lat)) *
            func.sin(func.radians(self.Model.lat))
        )

        query = select(self.Model).where(
            and_(
                func.lower(self.Model.name) == name.lower(),
                haversine > min_distance_km
            )
        )

        result = await self.session.execute(query)
        return result.scalars().all()
