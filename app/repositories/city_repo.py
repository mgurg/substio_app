from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.database.models.models import City
from app.exceptions import NotFoundError
from app.repositories.generics import GenericRepo


class CityRepo(GenericRepo[City]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, City)

    async def get_by_uuid(self, uuid: UUID) -> City:
        query = select(self.model).where(self.model.uuid == uuid)

        result = await self.session.execute(query)
        city = result.scalar_one_or_none()
        if city is None:
            raise NotFoundError("City", str(uuid))

        return city

    async def find_by_teryt(self, teryt: str) -> City | None:
        query = select(self.model).where(
            self.model.teryt_simc == teryt
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_partial_name(self, name: str) -> Sequence[City]:
        query = select(self.model).where(func.lower(self.model.name_ascii).ilike(f"%{name}%")).order_by(
            desc(self.model.importance)).limit(5)
        result = await self.session.execute(query)
        return result.scalars().all()
