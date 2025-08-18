import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Query, UploadFile
from loguru import logger
from openai import AsyncOpenAI
from sqlalchemy import Sequence
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from app.config import get_settings
from app.database.models.enums import OfferStatus, SourceType
from app.database.models.models import Offer
from app.database.repository.CityRepo import CityRepo
from app.database.repository.LegalRoleRepo import LegalRoleRepo
from app.database.repository.OfferRepo import OfferRepo
from app.database.repository.PlaceRepo import PlaceRepo
from app.schemas.api.api_responses import ParseResponse, SubstitutionOffer, UsageDetails
from app.schemas.rest.requests import FacebookPost, OfferAdd, OfferUpdate
from app.schemas.rest.responses import ImportResult, RawOfferIndexResponse

settings = get_settings()

TIMESTAMP_PATTERN = re.compile(r"(\d{8})_(\d{6})")


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


def parse_facebook_post_to_offer(post: FacebookPost, filename: str) -> "OfferAdd":
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

    return OfferAdd(
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
            legal_role_repo: Annotated[LegalRoleRepo, Depends()]
    ) -> None:
        self.offer_repo = offer_repo
        self.place_repo = place_repo
        self.city_repo = city_repo
        self.legal_role_repo = legal_role_repo

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

    async def create(self, offer: OfferAdd) -> None:
        db_offer = await self.offer_repo.get_by_offer_uid(offer.offer_uid)
        if db_offer:
            raise HTTPException(status_code=HTTP_409_CONFLICT,
                                detail=f"Offer with {offer.offer_uid} already exists")

        offer_data = {
            "uuid": str(uuid4()),
            "author": offer.author,
            "author_uid": offer.author_uid,
            "offer_uid": offer.offer_uid,
            "raw_data": offer.raw_data,
            "added_at": offer.timestamp,
            "source": offer.source
        }

        await self.offer_repo.create(**offer_data)
        return None

    async def parse_raw(self, offer_uuid: UUID) -> ParseResponse:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid)

        if not db_offer or not db_offer.raw_data:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Offer `{offer_uuid}` not found!")

        try:
            # Use async OpenAI client
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

        if not db_offer or not db_offer.raw_data:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Offer `{offer_uuid}` not found!")

        update_data = offer_update.model_dump(exclude_unset=True)
        legal_roles_data = update_data.pop("roles", None)
        facility_uuid = update_data.pop("facility_uuid", None)
        city_uuid = update_data.pop("city_uuid", None)

        date_str = update_data.pop("date", None)
        hour_str = update_data.pop("hour", None)

        # Apply simple scalar field updates
        for field, value in update_data.items():
            setattr(db_offer, field, value)

        if date_str and hour_str:
            try:
                combined = datetime.strptime(f"{date_str} {hour_str}", "%Y-%m-%d %H:%M")
                warsaw_tz = ZoneInfo("Europe/Warsaw")
                local_dt = combined.replace(tzinfo=warsaw_tz)
                utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
                db_offer.valid_to = utc_dt
            except ValueError as e:
                raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid date/hour format") from e
        else:
            utc_now = datetime.now(tz=ZoneInfo("UTC"))
            db_offer.valid_to = utc_now + timedelta(days=4)

        # Apply simple scalar field updates
        for field, value in update_data.items():
            setattr(db_offer, field, value)

        # Update M2M legal_roles
        if legal_roles_data is not None:
            roles = await self.legal_role_repo.get_by_uuids(legal_roles_data)
            db_offer.legal_roles.clear()
            db_offer.legal_roles.extend(roles)
        #
        # # Update relation to place
        if facility_uuid is not None:
            place = await self.place_repo.get_by_uuid(facility_uuid)
            if place is None:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Place `{facility_uuid}` not found!")
            db_offer.place = place

        if city_uuid is not None:
            city = await self.city_repo.get_by_uuid(city_uuid)
            if city is None:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"City `{city_uuid}` not found!")
            db_offer.city = city
        #
        # # Persist the changes
        await self.offer_repo.update(db_offer.id, **update_data)

        return None

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
            OfferStatus.ACCEPTED, search, ["legal_roles", "place", "city"],
            lat=lat, lon=lon, distance_km=distance_km,
            legal_role_uuids=legal_role_uuids, invoice=invoice
        )
        return db_offers, count

        return db_offers, count

    async def get_raw(self, offer_uuid: UUID) -> RawOfferIndexResponse:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid, ["legal_roles", "place", "city"])

        return db_offer

    async def get_legal_roles(self):
        return await self.legal_role_repo.get_all()
