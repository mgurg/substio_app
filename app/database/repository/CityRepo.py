from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select, Sequence, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.database.models.models import City
from app.database.repository.generics import GenericRepo

UserDB = Annotated[AsyncSession, Depends(get_db)]


class CityRepo(GenericRepo[City]):
    def __init__(self, session: UserDB) -> None:
        self.Model = City
        super().__init__(session, self.Model)

    async def get_by_uuid(self, uuid: UUID) -> City | None:
        query = select(self.Model).where(self.Model.uuid == uuid)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> City | None:
        query = select(self.Model).where(func.lower(self.Model.name).ilike(f"%{name.lower()}%")).limit(5)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_partial_name(self, name: str) -> Sequence[City]:
        query = select(self.Model).where(func.lower(self.Model.name_ascii).ilike(f"%{name}%")).order_by(desc(self.Model.importance)).limit(5)
        result = await self.session.execute(query)
        return result.scalars().all()