from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.models import LegalRole
from app.repositories.generics import GenericRepo


class LegalRoleRepo(GenericRepo[LegalRole]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LegalRole)

    async def get_by_uuid(self, uuid: UUID) -> LegalRole | None:
        query = select(self.model).where(self.model.uuid == uuid)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_uuids(self, uuids: list[UUID]) -> Sequence[LegalRole]:
        query = select(self.model).where(self.model.uuid.in_(uuids))

        result = await self.session.execute(query)
        return result.scalars().all()
