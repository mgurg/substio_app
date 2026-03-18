import json
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException, UploadFile
from loguru import logger
from sqlalchemy import Sequence
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from app.common.email.EmailNotifierBase import EmailNotifierBase
from app.common.slack.SlackNotifierBase import SlackNotifierBase
from app.core.config import get_settings
from app.database.models.enums import OfferStatus, SourceType
from app.database.models.models import Offer
from app.database.repository.CityRepo import CityRepo
from app.database.repository.filters.offer_filters import OfferFilters
from app.database.repository.LegalRoleRepo import LegalRoleRepo
from app.database.repository.OfferRepo import OfferRepo
from app.database.repository.PlaceRepo import PlaceRepo
from app.schemas.api.api_responses import ParseResponse
from app.schemas.rest.requests import FacebookPost, OfferAdd, OfferRawAdd, OfferUpdate
from app.schemas.rest.responses import ImportResult
from app.service.EmailValidationService import EmailValidationService
from app.service.parsers.base import AIParser
from app.utils.email_utils import extract_and_fix_email
from app.utils.timestamp_utils import extract_timestamp_from_filename

settings = get_settings()


def parse_facebook_post_to_offer(post: FacebookPost, filename: str) -> "OfferRawAdd":
    """
    Convert a FacebookPost model into an OfferAdd object.
    Falls back to the filename timestamp or current datetime if date_posted is missing/invalid.
    """
    timestamp = datetime.now(UTC)

    if post.date_posted:
        try:
            timestamp = datetime.fromisoformat(post.date_posted)
        except ValueError:
            if filename:
                timestamp = extract_timestamp_from_filename(filename)
    elif filename:
        timestamp = extract_timestamp_from_filename(filename)

    return OfferRawAdd(
        raw_data=post.post_content,
        author=post.user_name,
        author_uid=post.user_profile_url,
        offer_uid=post.post_url,
        timestamp=timestamp,
        source=SourceType.BOT,
    )


class OfferService:
    def __init__(
        self,
        offer_repo: OfferRepo,
        place_repo: PlaceRepo,
        city_repo: CityRepo,
        legal_role_repo: LegalRoleRepo,
        slack_notifier: SlackNotifierBase,
        email_notifier: EmailNotifierBase,
        ai_parser: AIParser,
        email_validator: EmailValidationService,
    ) -> None:
        self.offer_repo = offer_repo
        self.place_repo = place_repo
        self.city_repo = city_repo
        self.legal_role_repo = legal_role_repo
        self.slack_notifier = slack_notifier
        self.email_notifier = email_notifier
        self.ai_parser = ai_parser
        self.email_validator = email_validator

    async def import_raw_offers(self, file: UploadFile) -> ImportResult:
        self._validate_json_upload(file)
        try:
            json_data = self._parse_json_upload(await file.read())
        except HTTPException:
            raise
        except json.JSONDecodeError as err:
            raise HTTPException(status_code=400, detail="Invalid JSON file") from err
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}") from e

        import_result = ImportResult(total_records=len(json_data), imported_records=0, skipped_records=0, errors=[])

        for i, post_data in enumerate(json_data, start=1):
            await self._import_single_post(post_data, file.filename, i, import_result)

        return import_result

    async def create_raw_offer(self, offer: OfferRawAdd) -> None:
        db_offer = await self.offer_repo.get_by_offer_uid(offer.offer_uid)
        if db_offer:
            raise HTTPException(status_code=HTTP_409_CONFLICT, detail=f"Offer with {offer.offer_uid} already exists")
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

        date_obj, hour_obj = self._parse_date_hour(relations["date_str"], relations["hour_str"])
        self._apply_datetime_data(offer_data, date_obj, hour_obj)
        await self._apply_offer_location_data(offer_data, relations["facility_uuid"], relations["city_uuid"])
        await self._apply_offer_roles(offer_data, relations["roles_uuids"], require_all=True)

        await self.offer_repo.create(**offer_data)

        if offer_add.source != SourceType.BOT:
            await self.slack_notifier.send_new_offer_notification(
                author=offer_add.author, email=offer_add.email, description=offer_add.description, offer_uuid=offer_uuid
            )
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

        # Extract special fields
        relations = self._extract_offer_relations(update_data)
        submit_email = update_data.pop("submit_email", None)

        # Apply basic updates
        for field, value in update_data.items():
            setattr(db_offer, field, value)

        # Handle complex updates through helper methods
        await self._update_datetime_fields(db_offer, relations["date_str"], relations["hour_str"])
        await self._update_legal_roles(db_offer, relations["roles_uuids"])
        await self._update_facility(db_offer, relations["facility_uuid"])
        await self._update_city(db_offer, relations["city_uuid"])

        await self.offer_repo.update(db_offer.id, **update_data)
        updated_offer = await self.offer_repo.get_by_uuid(offer_uuid, [])

        # Send email if needed
        if self.email_validator.should_send_offer_email(updated_offer, db_offer, submit_email):
            await self._send_offer_imported_notification(updated_offer, db_offer.uuid)

        return None

    async def _update_datetime_fields(self, db_offer: Offer, date_str: str | None, hour_str: str | None) -> None:
        """Handle date/hour parsing and valid_to computation"""
        date_obj, hour_obj = self._parse_date_hour(date_str, hour_str)
        self._apply_datetime_fields(db_offer, date_obj, hour_obj)

    def _parse_date(self, date_str: str) -> date:
        """Parse date string with error handling"""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid date format") from e

    def _parse_hour(self, hour_str: str) -> time:
        """Parse hour string with error handling"""
        try:
            return datetime.strptime(hour_str, "%H:%M").time()
        except ValueError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid hour format") from e

    def _compute_valid_to(self, date_obj: date | None, hour_obj: time | None) -> datetime:
        """Compute valid_to timestamp based on date and hour"""
        if date_obj and hour_obj:
            combined = datetime.combine(date_obj, hour_obj)
            warsaw_tz = ZoneInfo("Europe/Warsaw")
            return combined.replace(tzinfo=warsaw_tz).astimezone(ZoneInfo("UTC"))

        return datetime.now(UTC) + timedelta(days=7)

    async def _update_legal_roles(self, db_offer: Offer, roles_uuids: list | None) -> None:
        """Update legal roles if provided"""
        if roles_uuids is not None:
            roles = await self._load_roles(roles_uuids, require_all=False)
            db_offer.legal_roles.clear()
            db_offer.legal_roles.extend(roles)

    async def _update_facility(self, db_offer: Offer, facility_uuid: UUID | None) -> None:
        """Update facility/place if provided"""
        if facility_uuid is not None:
            place = await self.place_repo.get_by_uuid(facility_uuid)
            self._assign_place_to_offer(db_offer, place)

    async def _update_city(self, db_offer: Offer, city_uuid: UUID | None) -> None:
        """Update city if provided"""
        if city_uuid is not None:
            city = await self.city_repo.get_by_uuid(city_uuid)
            self._assign_city_to_offer(db_offer, city)

    async def _send_offer_imported_notification(self, offer: Offer, offer_uuid: str) -> None:
        """Send email notification for imported offer"""
        recipient_email = offer.email
        recipient_name = offer.author or "User"

        success = await self.email_notifier.send_offer_imported_email(
            recipient_email=recipient_email, recipient_name=recipient_name, offer_uuid=offer_uuid
        )

        if success:
            logger.info(f"Email notification sent successfully to {recipient_email} for offer {offer_uuid}")
        else:
            logger.warning(f"Failed to send email notification for offer {offer_uuid}")

    async def list_map_offers(self, offset: int, limit: int, sort_column: str, sort_order: str, filters: OfferFilters):
        db_offers, count = await self.offer_repo.get_offers(
            offset, limit, sort_column, sort_order, filters, ["place", "city"]
        )

        return db_offers, count

    async def list_raw_offers(
        self, offset: int, limit: int, sort_column: str, sort_order: str, filters: OfferFilters
    ) -> tuple[Sequence[Offer], int]:
        filters.load_relations = ["legal_roles", "place", "city"]
        filters.search_fields = ["offer_uid", "raw_data", "author"]
        if sort_column == "name":
            sort_column = "author"

        db_offers, count = await self.offer_repo.get_offers(
            offset, limit, sort_column, sort_order, filters, ["legal_roles", "place", "city"]
        )

        return db_offers, count

    async def list_offers(
        self, offset: int, limit: int, sort_column: str, sort_order: str, filters: OfferFilters
    ) -> tuple[Sequence[Offer], int]:
        filters.load_relations = ["legal_roles", "place", "city"]
        db_offers, count = await self.offer_repo.get_offers(
            offset, limit, sort_column, sort_order, filters, ["legal_roles", "place", "city"]
        )
        return db_offers, count

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

    async def get_raw_offer(self, offer_uuid: UUID) -> Offer:
        return await self.offer_repo.get_by_uuid(offer_uuid, ["legal_roles", "place", "city"])

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

    def _validate_json_upload(self, file: UploadFile) -> None:
        if not file.filename or not file.filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="File must be a JSON file")

    def _parse_json_upload(self, content: bytes) -> list[dict]:
        json_data = json.loads(content.decode("utf-8"))
        if not isinstance(json_data, list):
            raise HTTPException(status_code=400, detail="JSON file must contain an array of posts")
        return json_data

    async def _import_single_post(
        self, post_data: dict, filename: str | None, index: int, import_result: ImportResult
    ) -> None:
        try:
            post = FacebookPost.model_validate(post_data)
            if "nieaktualne" in post.post_content.lower():
                import_result.skipped_records += 1
                import_result.errors.append(f"Record {index + 1}: nieaktualne")
                return

            offer = parse_facebook_post_to_offer(post, filename)
            await self.create_raw_offer(offer)
            import_result.imported_records += 1

        except HTTPException as e:
            if e.status_code == 409:
                import_result.skipped_records += 1
                import_result.errors.append(f"Record {index + 1}: {e.detail}")
            else:
                import_result.errors.append(f"Record {index + 1}: {e.detail}")
        except Exception as e:
            import_result.errors.append(f"Record {index + 1}: {str(e)}")

    def _extract_offer_relations(self, offer_data: dict) -> dict:
        return {
            "facility_uuid": offer_data.pop("facility_uuid", None),
            "city_uuid": offer_data.pop("city_uuid", None),
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
            "status": offer_data.get("status") or OfferStatus.ACTIVE,
        }

    def _parse_date_hour(self, date_str: str | None, hour_str: str | None) -> tuple[date | None, time | None]:
        date_obj = self._parse_date(date_str) if date_str else None
        hour_obj = self._parse_hour(hour_str) if hour_str else None
        return date_obj, hour_obj

    def _apply_datetime_data(self, offer_data: dict, date_obj: date | None, hour_obj: time | None) -> None:
        if date_obj:
            offer_data["date"] = date_obj
        if hour_obj:
            offer_data["hour"] = hour_obj
        offer_data["valid_to"] = self._compute_valid_to(date_obj, hour_obj)

    def _apply_datetime_fields(self, db_offer: Offer, date_obj: date | None, hour_obj: time | None) -> None:
        if date_obj:
            db_offer.date = date_obj
        if hour_obj:
            db_offer.hour = hour_obj
        db_offer.valid_to = self._compute_valid_to(date_obj, hour_obj)

    async def _apply_offer_location_data(
        self, offer_data: dict, facility_uuid: UUID | None, city_uuid: UUID | None
    ) -> None:
        if facility_uuid:
            place = await self.place_repo.get_by_uuid(facility_uuid)
            self._assign_place_to_data(offer_data, place)

        if city_uuid:
            city = await self.city_repo.get_by_uuid(city_uuid)
            self._assign_city_to_data(offer_data, city)

    async def _apply_offer_roles(
        self, offer_data: dict, roles_uuids: list | None, require_all: bool
    ) -> None:
        if roles_uuids:
            offer_data["legal_roles"] = await self._load_roles(roles_uuids, require_all=require_all)

    async def _load_roles(self, roles_uuids: list, require_all: bool) -> list:
        roles = await self.legal_role_repo.get_by_uuids(roles_uuids)
        if require_all and len(roles) != len(set(roles_uuids)):
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Legal role not found")
        return roles

    def _assign_place_to_data(self, offer_data: dict, place) -> None:
        offer_data["place_id"] = place.id
        offer_data["lat"] = place.lat
        offer_data["lon"] = place.lon

    def _assign_city_to_data(self, offer_data: dict, city) -> None:
        offer_data["city_id"] = city.id
        offer_data["lat"] = city.lat
        offer_data["lon"] = city.lon

    def _assign_place_to_offer(self, db_offer: Offer, place) -> None:
        db_offer.lat = place.lat
        db_offer.lon = place.lon
        db_offer.place = place

    def _assign_city_to_offer(self, db_offer: Offer, city) -> None:
        db_offer.lat = city.lat
        db_offer.lon = city.lon
        db_offer.city = city
