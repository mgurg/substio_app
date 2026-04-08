from datetime import UTC, date, datetime, time
from uuid import UUID, uuid4

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import Sequence
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from app.core.config import get_settings
from app.database.models.enums import OfferStatus, SourceType
from app.database.models.models import Offer
from app.infrastructure.ai.parsers.base import AIParser
from app.repositories.city_repo import CityRepo
from app.repositories.filters.offer_filters import OfferFilters
from app.repositories.legal_role_repo import LegalRoleRepo
from app.repositories.offer_repo import OfferRepo
from app.repositories.place_repo import PlaceRepo
from app.schemas.domain.ai import ParseResponse
from app.schemas.domain.offer import OfferAdd, OfferRawAdd, OfferUpdate
from app.services.email_validation_service import EmailValidationService
from app.services.offers.offer_date_handler import OfferDateHandler
from app.services.offers.offer_location_mapper import OfferLocationMapper
from app.services.offers.offer_notification_service import OfferNotificationService
from app.services.offers.offer_role_mapper import OfferRoleMapper

settings = get_settings()


class OfferService:
    def __init__(
        self,
        offer_repo: OfferRepo,
        place_repo: PlaceRepo,
        city_repo: CityRepo,
        legal_role_repo: LegalRoleRepo,
        ai_parser: AIParser,
        email_validator: EmailValidationService,
        notification_service: OfferNotificationService,
    ) -> None:
        self.offer_repo = offer_repo
        self.place_repo = place_repo
        self.city_repo = city_repo
        self.legal_role_repo = legal_role_repo
        self.ai_parser = ai_parser
        self.email_validator = email_validator
        self.notification_service = notification_service

    async def create_raw_offer(self, offer: OfferRawAdd) -> None:
        db_offer = await self.offer_repo.get_by_offer_uid(offer.offer_uid)
        if db_offer:
            raise HTTPException(status_code=HTTP_409_CONFLICT, detail=f"Offer with {offer.offer_uid} already exists")

        from app.utils.email_utils import extract_and_fix_email

        email = None
        if isinstance(offer.raw_data, str):
            email = extract_and_fix_email(offer.raw_data)

        offer_data = {
            "uuid": str(uuid4()),
            "author": offer.author,
            "author_uid": offer.author_uid,
            "offer_uid": offer.offer_uid,
            "raw_data": offer.raw_data,
            "added_at": offer.timestamp,
            "source": offer.source,
            "status": OfferStatus.POSTPONED,
        }

        if email:
            offer_data["email"] = email
            offer_data["status"] = OfferStatus.NEW

        await self.offer_repo.create(**offer_data)
        return None

    async def create_offer(self, offer_add: OfferAdd):
        offer_uuid = str(uuid4())
        offer_data = offer_add.model_dump(exclude_unset=True)
        relations = self._extract_offer_relations(offer_data)

        offer_data.update(self._system_offer_fields(offer_data, offer_uuid))

        date_obj, hour_obj = OfferDateHandler.parse_date_hour(relations["date_str"], relations["hour_str"])
        self._apply_datetime_data(offer_data, date_obj, hour_obj)
        await self._apply_offer_location_data(
            offer_data, relations["facility_uuid"], relations["city_uuid"], relations["place_name"], relations["city_name"]
        )
        await OfferRoleMapper.apply_offer_roles(offer_data, self.legal_role_repo, relations["roles_uuids"], require_all=True)

        await self.offer_repo.create(**offer_data)

        # Notify via Slack
        await self.notification_service.notify_new_offer_slack(offer_add, offer_uuid)

        # Notify via Email if conditions met
        new_offer = await self.offer_repo.get_by_uuid(UUID(offer_uuid))
        if self.email_validator.should_send_user_offer_creation_email(new_offer):
            await self.notification_service.send_user_offer_created_email(new_offer)

        return None

    async def parse_raw_offer(self, offer_uuid: UUID) -> ParseResponse:
        """Parse raw offer data using the configured AI parser."""
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid)

        if not db_offer.raw_data:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Offer `{offer_uuid}` has no data to parse!")

        try:
            return await self.ai_parser.parse_offer(db_offer.raw_data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error parsing offer {offer_uuid}: {e}")
            return ParseResponse(success=False, error=str(e), data=None)

    async def update_offers(self, offer_uuid: UUID, offer_update: OfferUpdate) -> None:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid, ["legal_roles", "place"])

        update_data = offer_update.model_dump(exclude_unset=True)
        # Ensure status is not set to None if it's passed as null in JSON
        if "status" in update_data and update_data["status"] is None:
            update_data.pop("status")

        # Extract special fields
        relations = self._extract_offer_relations(update_data)
        submit_email = update_data.pop("submit_email", None)

        # Apply basic updates
        for field, value in update_data.items():
            setattr(db_offer, field, value)

        # Handle complex updates through helper methods
        await self._update_datetime_fields(db_offer, relations["date_str"], relations["hour_str"])
        await OfferRoleMapper.update_legal_roles(db_offer, self.legal_role_repo, relations["roles_uuids"])
        await self._update_facility(db_offer, relations["facility_uuid"], relations["place_name"])
        await self._update_city(db_offer, relations["city_uuid"], relations["city_name"])

        await self.offer_repo.update(db_offer.id, **update_data)
        updated_offer = await self.offer_repo.get_by_uuid(offer_uuid, [])

        # Send email if needed
        if self.email_validator.should_send_offer_email(updated_offer, db_offer, submit_email):
            await self.notification_service.send_offer_imported_email(updated_offer, db_offer.uuid)

        return None

    async def _update_datetime_fields(self, db_offer: Offer, date_str: str | None, hour_str: str | None) -> None:
        """Handle date/hour parsing and valid_to computation"""
        date_obj, hour_obj = OfferDateHandler.parse_date_hour(date_str, hour_str)
        self._apply_datetime_fields(db_offer, date_obj, hour_obj)

    async def _update_facility(self, db_offer: Offer, facility_uuid: UUID | None, place_name: str | None) -> None:
        """Update facility/place if provided"""
        if facility_uuid is not None:
            place = await self.place_repo.get_by_uuid(facility_uuid)
            OfferLocationMapper.assign_place_to_offer(db_offer, place, place_name)
        elif place_name is not None:
            db_offer.place_name = place_name

    async def _update_city(self, db_offer: Offer, city_uuid: UUID | None, city_name: str | None) -> None:
        """Update city if provided"""
        if city_uuid is not None:
            city = await self.city_repo.get_by_uuid(city_uuid)
            OfferLocationMapper.assign_city_to_offer(db_offer, city, city_name)
        elif city_name is not None:
            db_offer.city_name = city_name

    async def list_map_offers(self, offset: int, limit: int, sort_column: str, sort_order: str, filters: OfferFilters):
        return await self._get_paginated_offers(offset, limit, sort_column, sort_order, filters, ["place", "city"])

    async def list_raw_offers(
        self, offset: int, limit: int, sort_column: str, sort_order: str, filters: OfferFilters
    ) -> tuple[Sequence[Offer], int]:
        filters.load_relations = ["legal_roles", "place", "city"]
        filters.search_fields = ["offer_uid", "raw_data", "author"]
        if sort_column == "name":
            sort_column = "author"

        return await self._get_paginated_offers(offset, limit, sort_column, sort_order, filters, ["legal_roles", "place", "city"])

    async def list_offers(
        self, offset: int, limit: int, sort_column: str, sort_order: str, filters: OfferFilters
    ) -> tuple[Sequence[Offer], int]:
        filters.load_relations = ["legal_roles", "place", "city"]
        return await self._get_paginated_offers(offset, limit, sort_column, sort_order, filters, ["legal_roles", "place", "city"])

    async def _get_paginated_offers(
        self, offset: int, limit: int, sort_column: str, sort_order: str, filters: OfferFilters, load_relations: list[str]
    ) -> tuple[Sequence[Offer], int]:
        return await self.offer_repo.get_offers(
            offset, limit, sort_column, sort_order, filters, load_relations
        )

    async def get_similar_offers(self, offer_uuid: UUID) -> Sequence[Offer]:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid, ["legal_roles", "place", "city"])
        if not db_offer.email:
            return []

        db_offers = await self.offer_repo.get_by_email(db_offer.email)

        return db_offers

    async def get_offer_email(self, offer_uuid: UUID) -> str:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid)
        if not db_offer.email:
            logger.error(f"No email found for offer with UUID: {offer_uuid}")
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="No email found")
        return db_offer.email

    async def get_offer_by_id(self, offer_uuid: UUID) -> Offer:
        return await self.offer_repo.get_by_uuid(offer_uuid, ["legal_roles", "place", "city"])

    async def accept_raw_offer(self, offer_uuid: UUID) -> None:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid)
        if db_offer.status == OfferStatus.REJECTED:
            raise HTTPException(status_code=HTTP_409_CONFLICT, detail="Cannot accept rejected offer")
        if db_offer.status == OfferStatus.ACTIVE:
            return None
        await self.offer_repo.update(db_offer.id, **{"status": OfferStatus.ACTIVE})

        return None

    async def reject_raw_offer(self, offer_uuid: UUID) -> None:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid)
        await self.offer_repo.update(db_offer.id, **{"status": OfferStatus.REJECTED})

        return None

    async def get_legal_roles(self):
        return await self.legal_role_repo.get_all()

    async def offers_count(self):
        return await self.offer_repo.get_offers_count()

    def _extract_offer_relations(self, offer_data: dict) -> dict:
        return {
            "facility_uuid": offer_data.pop("facility_uuid", None),
            "city_uuid": offer_data.pop("city_uuid", None),
            "place_name": offer_data.pop("place_name", None),
            "city_name": offer_data.pop("city_name", None),
            "roles_uuids": offer_data.pop("roles", None),
            "date_str": offer_data.pop("date", None),
            "hour_str": offer_data.pop("hour", None),
        }

    def _system_offer_fields(self, offer_data: dict, offer_uuid: str) -> dict:
        return {
            "uuid": offer_uuid,
            "offer_uid": str(uuid4()),
            "author_uid": None,
            "raw_data": None,
            "added_at": datetime.now(UTC),
            "status": offer_data.get("status") if offer_data.get("status") is not None else OfferStatus.ACTIVE,
            "source": offer_data.get("source") if offer_data.get("source") is not None else SourceType.USER,
        }

    def _apply_datetime_data(self, offer_data: dict, date_obj: date | None, hour_obj: time | None) -> None:
        if date_obj:
            offer_data["date"] = date_obj
        if hour_obj:
            offer_data["hour"] = hour_obj
        offer_data["valid_to"] = OfferDateHandler.compute_valid_to(date_obj, hour_obj)

    def _apply_datetime_fields(self, db_offer: Offer, date_obj: date | None, hour_obj: time | None) -> None:
        if date_obj:
            db_offer.date = date_obj
        if hour_obj:
            db_offer.hour = hour_obj
        db_offer.valid_to = OfferDateHandler.compute_valid_to(date_obj, hour_obj)

    async def _apply_offer_location_data(
        self, offer_data: dict, facility_uuid: UUID | None, city_uuid: UUID | None, place_name: str | None, city_name: str | None
    ) -> None:
        if facility_uuid:
            place = await self.place_repo.get_by_uuid(facility_uuid)
            OfferLocationMapper.assign_place_to_data(offer_data, place, place_name)
        elif place_name:
            offer_data["place_name"] = place_name

        if city_uuid:
            city = await self.city_repo.get_by_uuid(city_uuid)
            OfferLocationMapper.assign_city_to_data(offer_data, city, city_name)
        elif city_name:
            offer_data["city_name"] = city_name
