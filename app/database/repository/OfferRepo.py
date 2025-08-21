from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import BinaryExpression, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.db import get_db
from app.database.models.enums import OfferStatus
from app.database.models.models import LegalRole, Offer, Place
from app.database.repository.generics import GenericRepo

UserDB = Annotated[AsyncSession, Depends(get_db)]


class OfferRepo(GenericRepo[Offer]):
    EARTH_RADIUS_KM = 6371  # Earth's radius in kilometers
    KM_PER_DEGREE_LAT = 111.0  # Approximate kilometers per degree of latitude

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

    async def get_by_uuid(self, uuid: UUID, load_relations: list[str] | str = None) -> Offer | None:
        query = select(self.Model).where(self.Model.uuid == uuid)
        query = self._apply_relationship_loading(query, load_relations)

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
            load_relations: list[str] | str = None,
            lat: float | None = None,
            lon: float | None = None,
            distance_km: float | None = None,
            legal_role_uuids: list[UUID] | None = None,
            invoice: bool | None = None
    ) -> tuple[Sequence[Offer], int]:

        query = select(self.Model)
        query = self._apply_relationship_loading(query, load_relations)

        search_filters = []

        if status is not None:
            search_filters.append(self.Model.status == status)

        if search is not None:
            search_filters.append(self.Model.description.ilike(f"%{search}%"))

        if invoice is not None:
            search_filters.append(self.Model.invoice == invoice)

        if legal_role_uuids is not None and len(legal_role_uuids) > 0:
            search_filters.append(
                self.Model.legal_roles.any(LegalRole.uuid.in_(legal_role_uuids))
            )

        # if all([lat is not None, lon is not None, distance_km is not None]):
        #     lat_diff = distance_km / self.KM_PER_DEGREE_LAT
        #     lon_diff = distance_km / (self.KM_PER_DEGREE_LAT * func.cos(func.radians(lat)))
        #
        #     distance_filter = self.Model.place.has(
        #         and_(
        #             Place.lat.between(lat - lat_diff, lat + lat_diff),
        #             Place.lon.between(lon - lon_diff, lon + lon_diff),
        #             func.acos(
        #                 func.sin(func.radians(lat)) * func.sin(func.radians(Place.lat)) +
        #                 func.cos(func.radians(lat)) * func.cos(func.radians(Place.lat)) *
        #                 func.cos(func.radians(Place.lon) - func.radians(lon))
        #             ) * self.EARTH_RADIUS_KM <= distance_km
        #         )
        #     )
        #     search_filters.append(distance_filter)
        if all([lat is not None, lon is not None, distance_km is not None]):
            lat_diff = distance_km / self.KM_PER_DEGREE_LAT
            lon_diff = distance_km / (self.KM_PER_DEGREE_LAT * func.cos(func.radians(lat)))

            distance_filter = and_(
                self.Model.lat.between(lat - lat_diff, lat + lat_diff),
                self.Model.lon.between(lon - lon_diff, lon + lon_diff),
                func.acos(
                    func.sin(func.radians(lat)) * func.sin(func.radians(self.Model.lat)) +
                    func.cos(func.radians(lat)) * func.cos(func.radians(self.Model.lat)) *
                    func.cos(func.radians(self.Model.lon) - func.radians(lon))
                ) * self.EARTH_RADIUS_KM <= distance_km
            )

            search_filters.append(distance_filter)
        # Apply all filters
        if search_filters:
            query = query.filter(and_(*search_filters))

        # Apply sorting
        query = query.order_by(getattr(getattr(self.Model, sort_column), sort_order)())

        # Execute main query
        result = await self.session.execute(query.offset(offset).limit(limit))

        count_query = select(func.count(self.Model.id))

        if legal_role_uuids is not None and len(legal_role_uuids) > 0:
            count_query = count_query.select_from(self.Model).join(self.Model.legal_roles).filter(
                LegalRole.uuid.in_(legal_role_uuids)
            )

        if all([lat is not None, lon is not None, distance_km is not None]):
            if legal_role_uuids is None or len(legal_role_uuids) == 0:
                count_query = count_query.select_from(self.Model).join(Place, self.Model.place_id == Place.id,
                                                                       isouter=True)
            else:
                count_query = count_query.join(Place, self.Model.place_id == Place.id, isouter=True)

        if search_filters:
            count_query = count_query.filter(and_(*search_filters))

        count_result = await self.session.execute(count_query)
        total_records = count_result.scalar_one()

        return result.scalars().all(), total_records
