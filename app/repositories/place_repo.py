from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.database.models.models import Place
from app.repositories.generics import GenericRepo

EARTH_RADIUS_KM = 6371.0


class PlaceRepo(GenericRepo[Place]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Place)

    async def get_by_uuid(self, uuid: UUID) -> Place:
        query = select(self.model).where(self.model.uuid == uuid)

        result = await self.session.execute(query)
        place = result.scalar_one_or_none()
        if place is None:
            raise NotFoundError("Place", str(uuid))

        return place

    async def get_by_partial_name(self, name: str, place_type: str | None = None) -> Sequence[Place]:
        conditions = [func.lower(self.model.name_ascii).ilike(f"%{name.lower()}%")]

        if place_type:
            conditions.append(self.model.type == place_type)

        query = select(self.model).where(and_(*conditions)).limit(7)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_name_and_distance(self, name: str, lat: float, lon: float, min_distance_km: float = 1.0) -> Sequence[Place]:
        haversine = EARTH_RADIUS_KM * func.acos(
            func.least(1.0, func.greatest(-1.0,
                func.cos(func.radians(lat)) *
                func.cos(func.radians(self.model.lat)) *
                func.cos(func.radians(self.model.lon) - func.radians(lon)) +
                func.sin(func.radians(lat)) *
                func.sin(func.radians(self.model.lat))
            ))
        )

        # Detect places WITHIN the given distance threshold (potential duplicates)
        query = select(self.model).where(
            and_(
                func.lower(self.model.name) == name.lower(),
                haversine < min_distance_km
            )
        )

        result = await self.session.execute(query)
        return result.scalars().all()
