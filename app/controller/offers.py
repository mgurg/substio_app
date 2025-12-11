from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from app.database.models.enums import OfferStatus
from app.database.repository.filters.offer_filters import OfferFilters
from app.schemas.api.api_responses import ParseResponse
from app.schemas.rest.requests import OfferAdd, OfferRawAdd, OfferUpdate
from app.schemas.rest.responses import (
    ImportResult,
    LegalRoleIndexResponse,
    OfferEmail,
    OfferIndexResponse,
    OfferMapResponse,
    OffersCount,
    OffersPaginated,
    RawOfferIndexResponse,
    RawOffersPaginated,
    SimilarOfferIndexResponse,
)
from app.service.OfferService import OfferService

offer_router = APIRouter()

offerServiceDependency = Annotated[OfferService, Depends()]


@offer_router.get("/legal_roles")
async def get_legal_roles(offer_service: offerServiceDependency) -> list[LegalRoleIndexResponse]:
    return await offer_service.get_legal_roles()


@offer_router.get("/count")
async def offers_count(offer_service: offerServiceDependency) -> OffersCount:
    count = await offer_service.offers_count()
    return OffersCount(count=count)


@offer_router.post("", status_code=HTTP_201_CREATED)
async def create_offer(offer_service: offerServiceDependency, offer_add: OfferAdd) -> None:
    await offer_service.create_offer(offer_add)

    return None


@offer_router.patch("/{offer_uuid}", status_code=HTTP_204_NO_CONTENT)
async def update_offer(offer_service: offerServiceDependency, offer_uuid: UUID, offer_update: OfferUpdate) -> None:
    return await offer_service.update_offers(offer_uuid, offer_update)


@offer_router.get("")
async def list_offers(
    offer_service: offerServiceDependency,
    search: Annotated[str | None, Query(max_length=50)] = None,
    limit: int = 10,
    offset: int = 0,
    field: Literal["valid_to", "created_at"] = "valid_to",
    order: Literal["asc", "desc"] = "asc",
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    distance_km: Annotated[float | None, Query(gt=0, le=1000)] = None,
    legal_role_uuids: Annotated[list[UUID] | None, Query()] = None,
    invoice: Annotated[bool | None, Query()] = None,
) -> OffersPaginated:
    location_params = [lat, lon, distance_km]
    if any(param is not None for param in location_params) and not all(param is not None for param in location_params):
        raise HTTPException(status_code=400, detail="lat, lon, and distance_km must all be provided together for location filtering")

    filters = OfferFilters(
        search=search,
        limit=limit,
        offset=offset,
        sort_column=field,
        sort_order=order,
        lat=lat,
        lon=lon,
        distance_km=distance_km,
        legal_role_uuids=legal_role_uuids,
        invoice=invoice,
        status=OfferStatus.ACTIVE,
        valid_to=datetime.now(UTC) - timedelta(hours=12),
    )

    db_offers, count = await offer_service.list_offers(offset, limit, field, order, filters)

    return OffersPaginated(data=db_offers, count=count, offset=offset, limit=limit)


@offer_router.get("/raw")
async def list_raw_offers(
    offer_service: offerServiceDependency,
    search: Annotated[str | None, Query(max_length=50)] = None,
    limit: int = 10,
    offset: int = 0,
    status: Annotated[OfferStatus | None, Query()] = None,
    field: Literal["name", "created_at"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
) -> RawOffersPaginated:
    filters = OfferFilters(search=search, limit=limit, offset=offset, sort_column=field, sort_order=order, status=status)

    db_offers, count = await offer_service.list_raw_offers(offset, limit, field, order, filters)

    return RawOffersPaginated(data=db_offers, count=count, offset=offset, limit=limit)


@offer_router.get("/map")
async def list_map_offers(offer_service: offerServiceDependency) -> list[OfferMapResponse]:
    filters = OfferFilters(limit=100, offset=0, status=OfferStatus.ACTIVE, valid_to=datetime.now(UTC) - timedelta(hours=12))

    db_offers, count = await offer_service.list_raw_offers(0, 100, "created_at", "desc", filters)

    return db_offers


@offer_router.get("/{offer_uuid}")
async def get_offer_by_id(offer_service: offerServiceDependency, offer_uuid: UUID) -> OfferIndexResponse:
    return await offer_service.get_offer_by_id(offer_uuid)


@offer_router.get("/{offer_uuid}/email")
async def get_offer_email(offer_service: offerServiceDependency, offer_uuid: UUID) -> OfferEmail:
    email = await offer_service.get_offer_email(offer_uuid)

    return OfferEmail(email=email)


@offer_router.get("/{offer_uuid}/similar")
async def get_similar_offers_by_user(offer_service: offerServiceDependency, offer_uuid: UUID) -> list[SimilarOfferIndexResponse]:
    return await offer_service.get_similar_offers(offer_uuid)


@offer_router.post("/raw", status_code=HTTP_201_CREATED)
async def create_raw_offer(offer_service: offerServiceDependency, offer_add: OfferRawAdd) -> None:
    await offer_service.create_raw_offer(offer_add)

    return None


@offer_router.post("/raw/import")
async def import_raw_offers(offer_service: offerServiceDependency, file: Annotated[UploadFile, File(...)]) -> ImportResult:
    return await offer_service.import_raw_offers(file)


@offer_router.get("/raw/{offer_uuid}")
async def get_raw_offer(offer_service: offerServiceDependency, offer_uuid: UUID) -> RawOfferIndexResponse:
    return await offer_service.get_raw_offer(offer_uuid)


@offer_router.get("/raw/{offer_uuid}/parse")
async def parse_raw_offer(offer_service: offerServiceDependency, offer_uuid: UUID) -> ParseResponse:
    return await offer_service.parse_raw_offer(offer_uuid)


@offer_router.patch("/raw/{offer_uuid}/accept", status_code=HTTP_204_NO_CONTENT)
async def accept_offer(offer_service: offerServiceDependency, offer_uuid: UUID) -> None:
    return await offer_service.accept_raw_offer(offer_uuid)


@offer_router.patch("/raw/{offer_uuid}/reject", status_code=HTTP_204_NO_CONTENT)
async def reject_offer(offer_service: offerServiceDependency, offer_uuid: UUID) -> None:
    return await offer_service.reject_raw_offer(offer_uuid)
