from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.email.EmailNotifierBase import EmailNotifierBase
from app.common.email.factory import get_email_notifier
from app.common.slack.factory import get_slack_notifier
from app.common.slack.SlackNotifierBase import SlackNotifierBase
from app.core.database import get_db
from app.repositories.city_repo import CityRepo
from app.repositories.legal_role_repo import LegalRoleRepo
from app.repositories.offer_repo import OfferRepo
from app.repositories.place_repo import PlaceRepo
from app.service.EmailValidationService import EmailValidationService
from app.service.OfferService import OfferService
from app.service.parsers.base import AIParser
from app.service.parsers.factory import get_ai_parser
from app.services.place_service import PlaceService


def get_city_repo(session: AsyncSession = Depends(get_db)) -> CityRepo:
    from app.repositories.city_repo import CityRepo
    return CityRepo(session)


def get_place_repo(session: AsyncSession = Depends(get_db)) -> PlaceRepo:
    from app.repositories.place_repo import PlaceRepo
    return PlaceRepo(session)


def get_offer_repo(session: AsyncSession = Depends(get_db)) -> OfferRepo:
    from app.repositories.offer_repo import OfferRepo
    return OfferRepo(session)


def get_legal_role_repo(session: AsyncSession = Depends(get_db)) -> LegalRoleRepo:
    from app.repositories.legal_role_repo import LegalRoleRepo
    return LegalRoleRepo(session)


def get_email_validator() -> EmailValidationService:
    from app.service.EmailValidationService import EmailValidationService
    return EmailValidationService()


def get_place_service(
        city_repo: CityRepo = Depends(get_city_repo),
        place_repo: PlaceRepo = Depends(get_place_repo),
) -> PlaceService:
    return PlaceService(city_repo=city_repo, place_repo=place_repo)


def get_offer_service(
        offer_repo: OfferRepo = Depends(get_offer_repo),
        place_repo: PlaceRepo = Depends(get_place_repo),
        city_repo: CityRepo = Depends(get_city_repo),
        legal_role_repo: LegalRoleRepo = Depends(get_legal_role_repo),
        slack_notifier: SlackNotifierBase = Depends(get_slack_notifier),
        email_notifier: EmailNotifierBase = Depends(get_email_notifier),
        ai_parser: AIParser = Depends(get_ai_parser),
) -> OfferService:

    return OfferService(
        offer_repo=offer_repo,
        place_repo=place_repo,
        city_repo=city_repo,
        legal_role_repo=legal_role_repo,
        slack_notifier=slack_notifier,
        email_notifier=email_notifier,
        ai_parser=ai_parser,
        email_validator=EmailValidationService(),
    )
