from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.database.models.enums import OfferStatus
from app.schemas.domain.common import Coordinates


class OfferFilters(BaseModel):
    offset: int = 0
    limit: int = 20
    sort_column: str = "created_at"
    sort_order: str = "desc"
    status: OfferStatus | None = None
    search: str | None = None
    search_fields: list[str] | None = None
    load_relations: list[str] | str | None = None
    coordinates: Coordinates | None = None
    distance_km: float | None = None
    legal_role_uuids: list[UUID] | None = None
    invoice: bool | None = None
    valid_to: datetime | None = None

    @property
    def has_location_filter(self) -> bool:
        return all([self.coordinates is not None, self.distance_km is not None])

    @property
    def has_legal_role_filter(self) -> bool:
        return self.legal_role_uuids is not None and len(self.legal_role_uuids) > 0
