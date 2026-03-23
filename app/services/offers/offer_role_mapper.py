from uuid import UUID

from fastapi import HTTPException
from starlette.status import HTTP_404_NOT_FOUND

from app.database.models.models import Offer
from app.repositories.legal_role_repo import LegalRoleRepo


class OfferRoleMapper:
    @staticmethod
    async def load_roles(legal_role_repo: LegalRoleRepo, roles_uuids: list[UUID], require_all: bool) -> list:
        """Load legal roles by UUIDs and validate existence if required."""
        roles = await legal_role_repo.get_by_uuids(roles_uuids)
        if require_all and len(roles) != len(set(roles_uuids)):
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Legal role not found")
        return roles

    @classmethod
    async def apply_offer_roles(
        cls, offer_data: dict, legal_role_repo: LegalRoleRepo, roles_uuids: list[UUID] | None, require_all: bool
    ) -> None:
        """Apply legal roles to offer data dictionary."""
        if roles_uuids:
            offer_data["legal_roles"] = await cls.load_roles(legal_role_repo, roles_uuids, require_all=require_all)

    @classmethod
    async def update_legal_roles(cls, db_offer: Offer, legal_role_repo: LegalRoleRepo, roles_uuids: list[UUID] | None) -> None:
        """Update legal roles on an existing Offer model."""
        if roles_uuids is not None:
            roles = await cls.load_roles(legal_role_repo, roles_uuids, require_all=False)
            db_offer.legal_roles.clear()
            db_offer.legal_roles.extend(roles)
