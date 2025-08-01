from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from starlette.status import HTTP_201_CREATED

from app.schemas.requests import OfferAdd
from app.schemas.responses import OffersPaginated, RawOffersPaginated
from app.service.OfferService import OfferService

offer_router = APIRouter()

offerServiceDependency = Annotated[OfferService, Depends()]


@offer_router.post("", status_code=HTTP_201_CREATED)
async def create(offer_service: offerServiceDependency, offer_add: OfferAdd) -> None:
    await offer_service.create(offer_add)

    return None


@offer_router.get("/")
async def read(offer_service: offerServiceDependency,
               search: Annotated[str | None, Query(max_length=50)] = None,
               limit: int = 10,
               offset: int = 0,
               field: Literal["name", "created_at"] = "created_at",
               order: Literal["asc", "desc"] = "asc",
               ) -> OffersPaginated:
    db_offers, count = await offer_service.read(offset, limit, field, order, search)

    return OffersPaginated(data=db_offers, count=count, offset=offset, limit=limit)


@offer_router.get("/raw")
async def read_raw(offer_service: offerServiceDependency,
                   search: Annotated[str | None, Query(max_length=50)] = None,
                   limit: int = 10,
                   offset: int = 0,
                   field: Literal["name", "created_at"] = "created_at",
                   order: Literal["asc", "desc"] = "asc",
                   ) -> RawOffersPaginated:
    db_offers, count = await offer_service.read_raw(offset, limit, field, order, search)

    return RawOffersPaginated(data=db_offers, count=count, offset=offset, limit=limit)
