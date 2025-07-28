from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import BinaryExpression, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.db import get_db
from app.database.models.enums import OfferStatus
from app.database.models.models import Offer
from app.database.repository.generics import GenericRepo

UserDB = Annotated[AsyncSession, Depends(get_db)]


class OfferRepo(GenericRepo[Offer]):
    def __init__(self, session: UserDB) -> None:
        self.Model = Offer
        super().__init__(session, self.Model)

    def _apply_relationship_loading(self, query, load_relations: list[str | BinaryExpression] = None):
        if not load_relations:
            return query

        for relation in load_relations:  # load_relations=["*"]
            if relation == "*":
                return query.options(selectinload("*"))
            elif isinstance(relation, str):  # load_relations=["city", "location"]
                query = query.options(selectinload(getattr(self.Model, relation)))
            elif isinstance(relation, BinaryExpression):  # load_relations=[Room.city, Room.location]
                query = query.options(selectinload(relation))

        return query

    async def get_by_uuid(self, uuid: UUID) -> Offer | None:
        query = select(self.Model).where(self.Model.uuid == uuid)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_offer_uid(self, offer_uid: str) -> Offer | None:
        query = select(self.Model).where(self.Model.offer_uid == offer_uid)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_offers(
            self,
            offset: int,
            limit: int,
            sort_column: str,
            sort_order: str,
            status: OfferStatus | None = None,
            search: str | None = None,
            load_relations: list[str] | str = None
    ) -> tuple[Sequence[Offer], int]:
        query = select(self.Model)
        query = self._apply_relationship_loading(query, load_relations)

        search_filters = []
        if status is not None:
            search_filters.append(self.Model.status == status)
            query = query.filter(*search_filters)

        if search is not None:
            search_filters.append(self.Model.description.ilike(f"%{search}%"))
            query = query.filter(*search_filters)

        query = query.order_by(getattr(getattr(self.Model, sort_column), sort_order)())
        result = await self.session.execute(query.offset(offset).limit(limit))

        total_records: int = 0

        count_query = select(func.count(self.Model.id))
        if search_filters:
            count_query = count_query.filter(*search_filters)

        count_result = await self.session.execute(count_query)
        total_records = count_result.scalar_one()

        return result.scalars().all(), total_records
