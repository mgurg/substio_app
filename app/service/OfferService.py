from typing import Annotated
from uuid import uuid4

from fastapi import Depends, HTTPException
from sqlalchemy import Sequence
from starlette.status import HTTP_409_CONFLICT

from app.database.models.enums import OfferStatus
from app.database.models.models import Offer
from app.database.repository.OfferRepo import OfferRepo
from app.schemas.requests import OfferAdd


class OfferService:
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
