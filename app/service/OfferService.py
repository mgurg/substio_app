import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Optional
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Query, UploadFile
from loguru import logger
from mailersend import MailerSendClient, EmailBuilder
from openai import AsyncOpenAI
from sqlalchemy import Sequence
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from app.common.slack.SlackNotifierBase import SlackNotifierBase
from app.common.slack.dependencies import get_slack_notifier
from app.config import get_settings
from app.database.models.enums import OfferStatus, SourceType
from app.database.models.models import Offer
from app.database.repository.CityRepo import CityRepo
from app.database.repository.LegalRoleRepo import LegalRoleRepo
from app.database.repository.OfferRepo import OfferRepo
from app.database.repository.PlaceRepo import PlaceRepo
from app.schemas.api.api_responses import ParseResponse, SubstitutionOffer, UsageDetails
from app.schemas.rest.requests import FacebookPost, OfferAdd, OfferRawAdd, OfferUpdate
from app.schemas.rest.responses import ImportResult, RawOfferIndexResponse, OfferIndexResponse

settings = get_settings()

TIMESTAMP_PATTERN = re.compile(r"(\d{8})_(\d{6})")
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def extract_and_fix_email(text: str) -> Optional[str]:
    """
    Extract email from text with simple domain fixing for .pl and .com

    Args:
        text: Raw text that might contain an email

    Returns:
        Valid email string or None if no valid email found
    """
    if not isinstance(text, str):
        return None

    email = try_extract_email(text)
    if email:
        return email

    fixed_text = apply_simple_fixes(text)
    return try_extract_email(fixed_text)


def try_extract_email(text: str) -> Optional[str]:
    """Try to extract email from text"""
    match = EMAIL_REGEX.search(text)
    if match:
        email = match.group(0).lower()
        # Basic validation - must contain @ and end with valid domain
        if '@' in email and (email.endswith('.pl') or email.endswith('.com') or
                             re.search(r'\.[a-z]{2,4}$', email)):
            return email
    return None


def apply_simple_fixes(text: str) -> str:
    """
    Strip off any junk after known valid TLDs
    """
    valid_tlds = ["pl", "com", "eu", "edu.pl", "org.pl", "net.pl", "com.pl"]

    for tld in valid_tlds:
        pattern = rf'(\.{tld})([a-zA-Z0-9_]+)\b'
        text = re.sub(pattern, r'\1', text, flags=re.IGNORECASE)

    text = re.sub(r'^\d+\.', '', text)

    return text


def extract_timestamp_from_filename(filename: str) -> datetime:
    """
    Extract timestamp from filename format: YYYYMMDD_HHMMSS.json
    Example: 20250819_110812.json -> 2025-08-19 11:08:12

    Falls back to the current datetime if parsing fails.
    """
    try:
        base_name = Path(filename).stem
        match = TIMESTAMP_PATTERN.search(base_name)
        if not match:
            return datetime.now()

        return datetime.strptime(
            f"{match.group(1)}_{match.group(2)}", "%Y%m%d_%H%M%S"
        )
    except Exception:
        return datetime.now()


def parse_facebook_post_to_offer(post: FacebookPost, filename: str) -> "OfferRawAdd":
    """
    Convert a FacebookPost model into an OfferAdd object.
    Falls back to the filename timestamp or current datetime if date_posted is missing/invalid.
    """
    timestamp = datetime.now()

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
    SYSTEM_PROMPT = """
    Z podanego opisu zastępstwa procesowego wyodrębnij następujące informacje:

    - `location`: Typ instytucji – wybierz jedną z: "sąd", "policja", "prokuratura". Ustaw `null`, jeśli nie można określić.
    - `location_full_name`: Pełna nazwa instytucji, np. "Sąd Rejonowy dla Warszawy-Mokotowa", lub `null`.
    - `date`: Lista dat zastępstwa w formacie **RRRR-MM-DD (np. 2025-07-30)**. Jeśli podana jest tylko jedna, zwróć listę z jednym elementem. Jeśli brak – `null`.
    - `time`: Lista godzin zastępstwa w formacie  **HH:MM** (24-godzinny format, np. 13:45). Jeśli brak – `null`.
    - `description`: Krótkie streszczenie charakteru sprawy lub kontekstu. **Usuń email** jeżeli występuje.
    - `legal_roles`: Lista grup docelowych – wybierz spośród: "adwokat", "radca prawny", "aplikant adwokacki", "aplikant radcowski". Jeśli brak informacji – `null`.
    - `email`: Adres e-mail, jeśli występuje w opisie. Jeśli nie ma – `null`.

    Zwróć dane w formacie JSON zgodnym ze schematem.
    """

    def __init__(
            self,
            offer_repo: Annotated[OfferRepo, Depends()],
            place_repo: Annotated[PlaceRepo, Depends()],
            city_repo: Annotated[CityRepo, Depends()],
            legal_role_repo: Annotated[LegalRoleRepo, Depends()],
            slack_notifier: SlackNotifierBase = Depends(get_slack_notifier)
    ) -> None:
        self.offer_repo = offer_repo
        self.place_repo = place_repo
        self.city_repo = city_repo
        self.legal_role_repo = legal_role_repo
        self.slack_notifier = slack_notifier

    async def upload(self, file: UploadFile) -> ImportResult:
        if not file.filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="File must be a JSON file")

        try:
            content = await file.read()
            json_data = json.loads(content.decode("utf-8"))

            if not isinstance(json_data, list):
                raise HTTPException(status_code=400, detail="JSON file must contain an array of posts")

            import_result = ImportResult(
                total_records=len(json_data),
                imported_records=0,
                skipped_records=0,
                errors=[]
            )

            for i, post_data in enumerate(json_data, start=1):
                try:
                    post = FacebookPost.model_validate(post_data)
                    if "nieaktualne" in post.post_content.lower():
                        import_result.skipped_records += 1
                        import_result.errors.append(f"Record {i + 1}: nieaktualne")
                        continue

                    offer = parse_facebook_post_to_offer(post, file.filename)
                    await self.create(offer)
                    import_result.imported_records += 1

                except HTTPException as e:
                    if e.status_code == 409:
                        import_result.skipped_records += 1
                        import_result.errors.append(f"Record {i + 1}: {e.detail}")
                    else:
                        import_result.errors.append(f"Record {i + 1}: {e.detail}")
                except Exception as e:
                    import_result.errors.append(f"Record {i + 1}: {str(e)}")

            return import_result

        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}") from e

    async def create(self, offer: OfferRawAdd) -> None:
        db_offer = await self.offer_repo.get_by_offer_uid(offer.offer_uid)
        if db_offer:
            raise HTTPException(status_code=HTTP_409_CONFLICT,
                                detail=f"Offer with {offer.offer_uid} already exists")
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

    async def create_by_user(self, offer_add: OfferAdd):
        offer_uuid = str(uuid4())
        offer_data = offer_add.model_dump(exclude_unset=True)

        # --- Extract relationship/derived fields ---
        facility_uuid = offer_data.pop("facility_uuid", None)
        city_uuid = offer_data.pop("city_uuid", None)
        roles_uuids = offer_data.pop("roles", None)
        date_str = offer_data.pop("date", None)
        hour_str = offer_data.pop("hour", None)

        # --- System fields ---
        offer_data.update({
            "uuid": offer_uuid,
            "offer_uid": str(uuid4()),
            "author_uid": None,
            "raw_data": None,
            "added_at": datetime.utcnow(),
            "status": offer_data.get("status") or OfferStatus.NEW,
        })

        # --- Handle date/hour ---
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
        hour_obj = datetime.strptime(hour_str, "%H:%M").time() if hour_str else None
        if date_obj:
            offer_data["date"] = date_obj
        if hour_obj:
            offer_data["hour"] = hour_obj

        # --- Compute valid_to ---
        if date_obj and hour_obj:
            combined = datetime.combine(date_obj, hour_obj)
            warsaw_tz = ZoneInfo("Europe/Warsaw")
            offer_data["valid_to"] = combined.replace(tzinfo=warsaw_tz).astimezone(ZoneInfo("UTC"))
        else:
            offer_data["valid_to"] = datetime.now(tz=ZoneInfo("UTC")) + timedelta(days=7)

        # --- Resolve facility/place ---
        if facility_uuid:
            place = await self.place_repo.get_by_uuid(facility_uuid)
            if not place:
                raise HTTPException(HTTP_404_NOT_FOUND, f"Place `{facility_uuid}` not found")
            offer_data["place_id"] = place.id
            offer_data["lat"] = place.lat
            offer_data["lon"] = place.lon

        # --- Resolve city ---
        if city_uuid:
            city = await self.city_repo.get_by_uuid(city_uuid)
            if not city:
                raise HTTPException(HTTP_404_NOT_FOUND, f"City `{city_uuid}` not found")
            offer_data["city_id"] = city.id
            offer_data["lat"] = city.lat
            offer_data["lon"] = city.lon

        # --- Resolve roles ---
        if roles_uuids:
            roles = await self.legal_role_repo.get_by_uuids(roles_uuids)
            offer_data["legal_roles"] = roles

        # --- Create in DB ---
        await self.offer_repo.create(**offer_data)

        offer_url = f"{settings.APP_URL}/raw/{offer_uuid}"
        review_url = f"{settings.APP_URL}/substytucje-procesowe/review-{offer_uuid}"
        await self.slack_notifier.send_message(
            f":tada: New offer created by *{offer_add.author}* \n email: {offer_add.email}\n description: {offer_add.description}.\n<{offer_url}|View Offer>\n<{review_url}|Review Offer>"
        )
        return None

    async def parse_raw(self, offer_uuid: UUID) -> ParseResponse:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid)

        if not db_offer or not db_offer.raw_data:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Offer `{offer_uuid}` not found!")

        try:
            client = AsyncOpenAI(api_key=settings.API_KEY_OPENAI)

            t = time.process_time()
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": settings.SYSTEM_PROMPT},
                    {"role": "user", "content": db_offer.raw_data},
                ],
                functions=[
                    {
                        "name": "generate_response",
                        "description": "Wygeneruj dane na podstawie opisu w języku polskim",
                        "parameters": SubstitutionOffer.model_json_schema(),
                    }
                ],
                function_call={"name": "generate_response"},
                temperature=1,
            )

            function_args = response.choices[0].message.function_call.arguments
            args_dict = json.loads(function_args)
            validated = SubstitutionOffer.model_validate(args_dict)

            elapsed_time = time.process_time() - t
            usage_info = UsageDetails(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                elapsed_time=elapsed_time
            )

            logger.info(
                f"Tokens prompt: {usage_info.prompt_tokens}, "
                f"completion: {usage_info.completion_tokens}, "
                f"total: {usage_info.total_tokens}, "
                f"took: {usage_info.elapsed_time:.3f} seconds"
            )

            return ParseResponse(success=True, data=validated, usage=usage_info)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating AI description: {e}")
            return ParseResponse(success=False, error=str(e), data=None)

    async def update(self, offer_uuid: UUID, offer_update: OfferUpdate) -> None:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid, ["legal_roles", "place"])

        if not db_offer:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Offer `{offer_uuid}` not found!")

        update_data = offer_update.model_dump(exclude_unset=True)
        legal_roles_data = update_data.pop("roles", None)
        facility_uuid = update_data.pop("facility_uuid", None)
        city_uuid = update_data.pop("city_uuid", None)
        submit_email = update_data.pop("submit_email", None)

        date_str = update_data.pop("date", None)
        hour_str = update_data.pop("hour", None)

        for field, value in update_data.items():
            setattr(db_offer, field, value)

        # --- Handle date/hour fields ---
        date_obj = None
        hour_obj = None

        if date_str:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                db_offer.date = date_obj
            except ValueError as e:
                raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid date format") from e

        if hour_str:
            try:
                hour_obj = datetime.strptime(hour_str, "%H:%M").time()
                db_offer.hour = hour_obj
            except ValueError as e:
                raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid hour format") from e

        # --- Compute valid_to ---
        if date_obj and hour_obj:
            combined = datetime.combine(date_obj, hour_obj)
            warsaw_tz = ZoneInfo("Europe/Warsaw")
            local_dt = combined.replace(tzinfo=warsaw_tz)
            utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
            db_offer.valid_to = utc_dt
        else:
            utc_now = datetime.now(tz=ZoneInfo("UTC"))
            db_offer.valid_to = utc_now + timedelta(days=7)

        if legal_roles_data is not None:
            roles = await self.legal_role_repo.get_by_uuids(legal_roles_data)
            db_offer.legal_roles.clear()
            db_offer.legal_roles.extend(roles)

        if facility_uuid is not None:
            place = await self.place_repo.get_by_uuid(facility_uuid)
            if place is None:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Place `{facility_uuid}` not found!")
            db_offer.lat = place.lat
            db_offer.lon = place.lon
            db_offer.place = place

        if city_uuid is not None:
            city = await self.city_repo.get_by_uuid(city_uuid)
            if city is None:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"City `{city_uuid}` not found!")
            db_offer.lat = city.lat
            db_offer.lon = city.lon
            db_offer.city = city

        await self.offer_repo.update(db_offer.id, **update_data)
        updated_offer = await self.offer_repo.get_by_uuid(offer_uuid, [])

        if not self.should_send_offer_email(updated_offer, db_offer, submit_email):
            return None

        recipient_email: str = updated_offer.email
        recipient_name: str = updated_offer.author or "User"

        logger.info(f"Sending email to {recipient_email}")

        ms = MailerSendClient(api_key=settings.API_KEY_MAILERSEND)
        email = (
            EmailBuilder()
            .from_email(settings.APP_ADMIN_MAIL, settings.APP_DOMAIN)
            .to_many([{"email": recipient_email, "name": recipient_name}])
            .bcc(settings.APP_ADMIN_MAIL)
            .subject("Substytucja - Twoje ogłoszenie zostało zaimportowane")
            .template("3zxk54vy71x4jy6v")
            .personalize_many([
                {
                    "email": recipient_email,
                    "data": {
                        "offer_url": f"{settings.APP_URL}/substytucje-procesowe/review-{db_offer.uuid}",
                        "website_name": settings.APP_DOMAIN,
                        "support_email": settings.APP_ADMIN_MAIL
                    }
                }
            ])
            .build()
        )
        logger.info(f"Sending email...")
        response = ms.emails.send(email)
        logger.info(f"Email sent! `{db_offer.uuid}`", response.data)

        return None

    def should_send_offer_email(self, updated_offer: Offer, db_offer: Offer, submit_email: bool) -> bool:
            if not updated_offer.email:
                logger.info("Skipping email sending: no email set on offer")
                return False

            if settings.APP_ENV != "PROD":
                logger.info("Skipping email sending: not running in PROD")
                return False

            if not submit_email:
                logger.info("Skipping email sending: submit_email is False")
                return False

            if updated_offer.status != OfferStatus.ACTIVE:
                logger.info(f"Skipping email sending: offer status is {updated_offer.status}")
                return False

            if db_offer.source != SourceType.BOT:
                logger.info(f"Skipping email sending: source is {db_offer.source}")
                return False

            return True
    async def read_raw(self, offset: int,
                       limit: int,
                       sort_column: str,
                       sort_order: str,
                       status: OfferStatus | None = None,
                       search: str | None = None) -> tuple[Sequence[Offer], int]:
        db_offers, count = await self.offer_repo.get_offers(offset, limit, sort_column, sort_order, status,
                                                            search, ["legal_roles", "place", "city"])

        return db_offers, count

    async def read(self, offset: int,
                   limit: int,
                   sort_column: str,
                   sort_order: str,
                   search: str | None = None,
                   lat: float | None = None,
                   lon: float | None = None,
                   distance_km: float | None = None,
                   legal_role_uuids: Annotated[list[UUID] | None, Query()] = None,
                   invoice: bool | None = None) -> tuple[Sequence[Offer], int]:

        db_offers, count = await self.offer_repo.get_offers(
            offset, limit, sort_column, sort_order,
            OfferStatus.ACTIVE, search, ["legal_roles", "place", "city"],
            lat=lat, lon=lon, distance_km=distance_km,
            legal_role_uuids=legal_role_uuids, invoice=invoice, valid_to=datetime.now(tz=ZoneInfo("UTC"))
        )
        return db_offers, count

    async def get_raw(self, offer_uuid: UUID) -> RawOfferIndexResponse:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid, ["legal_roles", "place", "city"])

        return db_offer

    async def get_offer(self, offer_uuid: UUID) -> OfferIndexResponse:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid, ["legal_roles", "place", "city"])

        return db_offer

    async def accept_offer(self, offer_uuid: UUID) -> None:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid)

        if not db_offer:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Offer `{offer_uuid}` not found!")

        update_data = {
            "status": OfferStatus.ACTIVE,
        }
        await self.offer_repo.update(db_offer.id, **update_data)
        return None

    async def reject_offer(self, offer_uuid: UUID) -> None:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid)

        if not db_offer:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Offer `{offer_uuid}` not found!")

        update_data = {
            "status": OfferStatus.REJECTED,
        }
        await self.offer_repo.update(db_offer.id, **update_data)
        return None

    async def get_legal_roles(self):
        return await self.legal_role_repo.get_all()
