from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.models import Place
from app.repository.generics import GenericRepo

UserDB = Annotated[AsyncSession, Depends(get_db)]


class PlaceRepo(GenericRepo[Place]):
    def __init__(self, session: UserDB) -> None:
        self.Model = Place
        super().__init__(session, self.Model)

    async def get_by_uuid(self, uuid: UUID) -> Place | None:
        query = select(self.Model).where(self.Model.uuid == uuid)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()
