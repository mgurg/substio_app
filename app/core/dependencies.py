from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.infrastructure.ai.parsers.base import AIParser
from app.infrastructure.ai.parsers.factory import get_ai_parser
from app.infrastructure.notifications.email.email_notifier_base import EmailNotifierBase
from app.infrastructure.notifications.email.factory import get_email_notifier
from app.infrastructure.notifications.slack.factory import get_slack_notifier
from app.infrastructure.notifications.slack.slack_notifier_base import SlackNotifierBase
from app.repositories.city_repo import CityRepo
from app.repositories.legal_role_repo import LegalRoleRepo
from app.repositories.offer_repo import OfferRepo
from app.repositories.place_repo import PlaceRepo
from app.services.email_validation_service import EmailValidationService
from app.services.offer_service import OfferService
from app.services.offers.offer_import_service import OfferImportService
from app.services.offers.offer_notification_service import OfferNotificationService
from app.services.place_service import PlaceService


def get_city_repo(session: AsyncSession = Depends(get_db)) -> CityRepo:
    return CityRepo(session)


def get_place_repo(session: AsyncSession = Depends(get_db)) -> PlaceRepo:
    return PlaceRepo(session)


def get_offer_repo(session: AsyncSession = Depends(get_db)) -> OfferRepo:
    return OfferRepo(session)


def get_legal_role_repo(session: AsyncSession = Depends(get_db)) -> LegalRoleRepo:
    return LegalRoleRepo(session)


def get_email_validator() -> EmailValidationService:
    return EmailValidationService()


def get_place_service(
        city_repo: CityRepo = Depends(get_city_repo),
        place_repo: PlaceRepo = Depends(get_place_repo),
) -> PlaceService:
    return PlaceService(city_repo=city_repo, place_repo=place_repo)


def get_offer_import_service(
    offer_repo: OfferRepo = Depends(get_offer_repo),
) -> OfferImportService:
    return OfferImportService(offer_repo=offer_repo)


def get_offer_notification_service(
    slack_notifier: SlackNotifierBase = Depends(get_slack_notifier),
    email_notifier: EmailNotifierBase = Depends(get_email_notifier),
) -> OfferNotificationService:
    return OfferNotificationService(
        slack_notifier=slack_notifier,
        email_notifier=email_notifier,
    )


def get_offer_service(
        offer_repo: OfferRepo = Depends(get_offer_repo),
        place_repo: PlaceRepo = Depends(get_place_repo),
        city_repo: CityRepo = Depends(get_city_repo),
        legal_role_repo: LegalRoleRepo = Depends(get_legal_role_repo),
        ai_parser: AIParser = Depends(get_ai_parser),
        email_validator: EmailValidationService = Depends(get_email_validator),
        offer_import_service: OfferImportService = Depends(get_offer_import_service),
        notification_service: OfferNotificationService = Depends(get_offer_notification_service),
) -> OfferService:
    return OfferService(
        offer_repo=offer_repo,
        place_repo=place_repo,
        city_repo=city_repo,
        legal_role_repo=legal_role_repo,
        ai_parser=ai_parser,
        email_validator=email_validator,
        offer_import_service=offer_import_service,
        notification_service=notification_service,
    )
