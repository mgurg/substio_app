from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.models import City
from app.repositories.generics import GenericRepo
from app.core.exceptions import NotFoundError


class CityRepo(GenericRepo[City]):
    def __init__(self, session: AsyncSession) -> None:
        self.Model = City
        super().__init__(session, self.Model)

    async def get_by_uuid(self, uuid: UUID) -> City:
        query = select(self.Model).where(self.Model.uuid == uuid)

        result = await self.session.execute(query)
        city = result.scalar_one_or_none()
        if city is None:
            raise NotFoundError("City", str(uuid))

        return city

    async def find_by_teryt(self, name: str) -> City | None:
        query = select(self.Model).where(
            self.Model.teryt_simc == name
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_partial_name(self, name: str) -> Sequence[City]:
        query = select(self.Model).where(func.lower(self.Model.name_ascii).ilike(f"%{name}%")).order_by(
            desc(self.Model.importance)).limit(5)
        result = await self.session.execute(query)
        return result.scalars().all()
