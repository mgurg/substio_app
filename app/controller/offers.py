from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from app.database.models.enums import OfferStatus
from app.schemas.api.api_responses import ParseResponse
from app.schemas.rest.requests import OfferAdd, OfferRawAdd, OfferUpdate
from app.schemas.rest.responses import ImportResult, LegalRoleIndexResponse, OffersPaginated, RawOfferIndexResponse, RawOffersPaginated
from app.service.OfferService import OfferService

offer_router = APIRouter()

offerServiceDependency = Annotated[OfferService, Depends()]


@offer_router.post("", status_code=HTTP_201_CREATED)
async def create_user_offer(offer_service: offerServiceDependency, offer_add: OfferAdd) -> None:
    await offer_service.create_by_user(offer_add)

    return None


@offer_router.post("/raw", status_code=HTTP_201_CREATED)
async def create_raw_offer(offer_service: offerServiceDependency, offer_add: OfferRawAdd) -> None:
    await offer_service.create(offer_add)

    return None


@offer_router.post("/import")
async def import_raw_offers(offer_service: offerServiceDependency, file: UploadFile = File(...),) -> ImportResult:
    return await offer_service.upload(file)


@offer_router.patch("/{offer_uuid}", status_code=HTTP_204_NO_CONTENT)
async def update_offer(offer_service: offerServiceDependency, offer_uuid: UUID, offer_update: OfferUpdate) -> None:
    return await offer_service.update(offer_uuid, offer_update)


@offer_router.get("/")
async def get_all_offers(offer_service: offerServiceDependency,
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
        raise HTTPException(
            status_code=400,
            detail="lat, lon, and distance_km must all be provided together for location filtering"
        )

    db_offers, count = await offer_service.read(
        offset, limit, field, order, search,
        lat=lat, lon=lon, distance_km=distance_km,
        legal_role_uuids=legal_role_uuids, invoice=invoice
    )

    return OffersPaginated(data=db_offers, count=count, offset=offset, limit=limit)


@offer_router.get("/raw")
async def get_all_raw_offers(offer_service: offerServiceDependency,
                             search: Annotated[str | None, Query(max_length=50)] = None,
                             limit: int = 10,
                             offset: int = 0,
                             status: Annotated[OfferStatus | None, Query()] = None,
                             field: Literal["name", "created_at"] = "created_at",
                             order: Literal["asc", "desc"] = "desc",
                             ) -> RawOffersPaginated:
    db_offers, count = await offer_service.read_raw(offset, limit, field, order, status, search)

    return RawOffersPaginated(data=db_offers, count=count, offset=offset, limit=limit)


@offer_router.get("/raw/{offer_uuid}")
async def get_raw_offer(offer_service: offerServiceDependency, offer_uuid: UUID) -> RawOfferIndexResponse:
    return await offer_service.get_raw(offer_uuid)


@offer_router.get("/legal_roles")
async def get_legal_roles(offer_service: offerServiceDependency) -> list[LegalRoleIndexResponse]:
    return await offer_service.get_legal_roles()


@offer_router.get("/parse/{offer_uuid}")
async def parse_raw(offer_service: offerServiceDependency, offer_uuid: UUID) -> ParseResponse:
    return await offer_service.parse_raw(offer_uuid)
