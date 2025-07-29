import json
import time
from typing import Annotated
from uuid import uuid4, UUID

from fastapi import Depends, HTTPException
from loguru import logger
from openai import AsyncOpenAI
from sqlalchemy import Sequence
from starlette.status import HTTP_409_CONFLICT, HTTP_404_NOT_FOUND

from app.config import get_settings
from app.database.models.enums import OfferStatus
from app.database.models.models import Offer
from app.database.repository.OfferRepo import OfferRepo
from app.schemas.api.api_responses import SubstitutionOffer, ParseResponse, UsageDetails
from app.schemas.rest.requests import OfferAdd, OfferUpdate

settings = get_settings()


class OfferService:
    SYSTEM_PROMPT = """
    Z podanego opisu zastępstwa procesowego wyodrębnij następujące informacje:

    - `location`: Typ instytucji – wybierz jedną z: "sąd", "policja", "prokuratura". Ustaw `null`, jeśli nie można określić.
    - `location_full_name`: Pełna nazwa instytucji, np. "Sąd Rejonowy dla Warszawy-Mokotowa", lub `null`.
    - `date`: Lista dat zastępstwa w formacie **RRRR-MM-DD (np. 2025-07-30)**. Jeśli podana jest tylko jedna, zwróć listę z jednym elementem. Jeśli brak – `null`.
    - `time`: Lista godzin zastępstwa w formacie  **HH:MM** (24-godzinny format, np. 13:45). Jeśli brak – `null`.
    - `description`: Krótkie streszczenie charakteru sprawy lub kontekstu. **Usuń email** jeżeli występuje.
    - `target_audience`: Lista grup docelowych – wybierz spośród: "adwokat", "radca prawny", "aplikant adwokacki", "aplikant radcowski". Jeśli brak informacji – `null`.
    - `email`: Adres e-mail, jeśli występuje w opisie. Jeśli nie ma – `null`.

    Zwróć dane w formacie JSON zgodnym ze schematem.
    """

    def __init__(
            self,
            offer_repo: Annotated[OfferRepo, Depends()]
    ) -> None:
        self.offer_repo = offer_repo

    async def create(self, offer: OfferAdd) -> None:
        db_company = await self.offer_repo.get_by_offer_uid(offer.offer_uid)
        if db_company:
            raise HTTPException(status_code=HTTP_409_CONFLICT,
                                detail=f"Offer with {offer.offer_uid} already exists")

        city_data = {
            "uuid": str(uuid4()),
            "author": offer.author,
            "author_uid": offer.author_uid,
            "offer_uid": offer.offer_uid,
            "raw_data": offer.raw_data,
            "added_at": offer.timestamp,
            "source": offer.source
        }

        await self.offer_repo.create(**city_data)
        return None

    async def parse_raw(self, offer_uuid: UUID) -> ParseResponse:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid)

        if not db_offer or not db_offer.raw_data:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Offer `{offer_uuid}` not found!")

        try:
            # Use async OpenAI client
            client = AsyncOpenAI(api_key=settings.API_KEY_OPENAI)
            from openai.types.chat import ChatCompletionMessageParam

            t = time.process_time()
            response = await client.chat.completions.create(  # Add await
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
                temperature=0.8,
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
                f"total: {usage_info.total_tokens}, "  # Added missing comma
                f"took: {usage_info.elapsed_time:.3f} seconds"  # Better formatting
            )

            return ParseResponse(success=True, data=validated, usage=usage_info)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating AI description: {e}")
            return ParseResponse(success=False, error=str(e), data=None)

    async def update(self, offer_uuid: UUID, offer_update: OfferUpdate) -> None:
        db_offer = await self.offer_repo.get_by_uuid(offer_uuid)

        if not db_offer or not db_offer.raw_data:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Offer `{offer_uuid}` not found!")

        update_data = offer_update.model_dump(exclude_unset=True)
        legal_roles_data = update_data.pop("legal_roles", None)

        for field, value in update_data.items():
            setattr(db_offer, field, value)

        if legal_roles_data is not None:
            ...
            # roles = await self.legal_role_repo.get_by_names(legal_roles_data)
            # db_offer.legal_roles.clear()
            # db_offer.legal_roles.extend(roles)

        await self.offer_repo.update(db_offer.id, **update_data)

        return None




    async def read_raw(self, offset: int,
                       limit: int,
                       sort_column: str,
                       sort_order: str,
                       status: OfferStatus | None = None,
                       search: str | None = None) -> tuple[Sequence[Offer], int]:
        db_offers, count = await self.offer_repo.get_offers(offset, limit, sort_column, sort_order, status,
                                                            search, [])

        return db_offers, count

    async def read(self, offset: int,
                   limit: int,
                   sort_column: str,
                   sort_order: str,
                   search: str | None = None) -> tuple[Sequence[Offer], int]:
        db_offers, count = await self.offer_repo.get_offers(offset, limit, sort_column, sort_order,
                                                            OfferStatus.ACCEPTED, search, [])

        return db_offers, count
