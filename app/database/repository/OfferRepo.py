from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import BinaryExpression, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.db import get_db
from app.database.models.enums import OfferStatus
from app.database.models.models import LegalRole, Offer, Place
from app.database.repository.filters.offer_filters import OfferFilters
from app.database.repository.generics import GenericRepo
from app.exceptions import NotFoundError

UserDB = Annotated[AsyncSession, Depends(get_db)]


class OfferRepo(GenericRepo[Offer]):
    EARTH_RADIUS_KM = 6371
    KM_PER_DEGREE_LAT = 111.0

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

    async def get_offers_count(self):

        count_query = select(func.count(self.Model.id)).where(self.Model.status == OfferStatus.ACTIVE).where(
            self.Model.valid_to > datetime.now(UTC))

        result = await self.session.execute(count_query)
        count = result.scalar_one()
        return count

    async def find_by_uuid(self, uuid: UUID, load_relations: list[str] | str = None) -> Offer | None:
        """Find offer by UUID. Returns None if not found (no exception)."""
        query = select(self.Model).where(self.Model.uuid == uuid)
        query = self._apply_relationship_loading(query, load_relations)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_uuid(self, uuid: UUID, load_relations: list[str] | str = None) -> Offer:
        """Find offer by UUID. Returns NotFoundError if not found."""
        query = select(self.Model).where(self.Model.uuid == uuid)
        query = self._apply_relationship_loading(query, load_relations)

        result = await self.session.execute(query)
        offer = result.scalar_one_or_none()

        if offer is None:
            raise NotFoundError("Offer", str(uuid))

        return offer

    async def get_by_offer_uid(self, offer_uid: str) -> Offer | None:
        query = select(self.Model).where(self.Model.offer_uid == offer_uid)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Sequence[Offer]:
        query = select(self.Model).where(self.Model.email == email).where(self.Model.valid_to.is_not(None))

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_offers(
            self,
            offset: int,
            limit: int,
            sort_column: str,
            sort_order: str,
            filters: OfferFilters,
            load_relations: list[str] | str = None,
    ) -> tuple[Sequence[Offer], int]:
        query = select(self.Model)
        query = self._apply_relationship_loading(query, load_relations)
        query = self._apply_filters(query, filters)
        query = query.order_by(getattr(getattr(self.Model, sort_column), sort_order)())

        result = await self.session.execute(query.offset(offset).limit(limit))
        items = result.scalars().all()

        count_query = self._build_count_query(filters)
        count_result = await self.session.execute(count_query)
        total_records = count_result.scalar_one()

        return items, total_records

    def _apply_filters(self, query, filters: OfferFilters):
        conditions = []

        if filters.status:
            conditions.append(self.Model.status == filters.status)

        if filters.search:
            conditions.append(self.Model.description.ilike(f"%{filters.search}%"))

        if filters.invoice is not None:
            conditions.append(self.Model.invoice == filters.invoice)

        if filters.valid_to:
            conditions.append(self.Model.valid_to > filters.valid_to)

        if filters.legal_role_uuids:
            conditions.append(
                self.Model.legal_roles.any(LegalRole.uuid.in_(filters.legal_role_uuids))
            )

        if all([filters.lat, filters.lon, filters.distance_km]):
            conditions.append(self._distance_filter(filters.lat, filters.lon, filters.distance_km))

        if conditions:
            query = query.filter(and_(*conditions))
        return query

    def _distance_filter(self, lat: float, lon: float, distance_km: float):
        lat_diff = distance_km / self.KM_PER_DEGREE_LAT
        lon_diff = distance_km / (self.KM_PER_DEGREE_LAT * func.cos(func.radians(lat)))

        return and_(
            self.Model.lat.between(lat - lat_diff, lat + lat_diff),
            self.Model.lon.between(lon - lon_diff, lon + lon_diff),
            func.acos(
                func.sin(func.radians(lat)) * func.sin(func.radians(self.Model.lat)) +
                func.cos(func.radians(lat)) * func.cos(func.radians(self.Model.lat)) *
                func.cos(func.radians(self.Model.lon) - func.radians(lon))
            ) * self.EARTH_RADIUS_KM <= distance_km
        )

    def _build_count_query(self, filters: OfferFilters):
        count_query = select(func.count(self.Model.id))
        count_query = count_query.select_from(self.Model)

        if filters.legal_role_uuids:
            count_query = count_query.join(self.Model.legal_roles)

        if all([filters.lat, filters.lon, filters.distance_km]) and not filters.legal_role_uuids:
            count_query = count_query.join(Place, self.Model.place_id == Place.id, isouter=True)

        return self._apply_filters(count_query, filters)
