from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.database.models.models import Place
from app.database.repository.generics import GenericRepo

UserDB = Annotated[AsyncSession, Depends(get_db)]


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

    async def get_by_name_and_street(self, name: str, street: str) -> Place | None:
        query = select(self.Model).where(
            and_(
                func.lower(self.Model.name) == name.lower(),
                self.Model.street_name == street
            )
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()
