import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from app.database.models.enums import OfferStatus, SourceType
from app.database.models.models import City, LegalRole, Offer
from app.repositories.city_repo import CityRepo
from app.repositories.legal_role_repo import LegalRoleRepo
from app.repositories.offer_repo import OfferRepo
from app.repositories.place_repo import PlaceRepo
from app.schemas.domain.offer import OfferAdd, OfferRawAdd, OfferUpdate
from app.services.email_validation_service import EmailValidationService
from app.services.offer_service import OfferService
from app.services.offers.offer_notification_service import OfferNotificationService


@pytest_asyncio.fixture
def offer_repo_mock():
    return AsyncMock(spec=OfferRepo)


@pytest_asyncio.fixture
def place_repo_mock():
    return AsyncMock(spec=PlaceRepo)


@pytest_asyncio.fixture
def city_repo_mock():
    return AsyncMock(spec=CityRepo)


@pytest_asyncio.fixture
def legal_role_repo_mock():
    return AsyncMock(spec=LegalRoleRepo)


@pytest_asyncio.fixture
def slack_notifier_mock():
    from app.infrastructure.notifications.slack.slack_notifier_base import SlackNotifierBase
    return AsyncMock(spec=SlackNotifierBase)


@pytest_asyncio.fixture
def email_notifier_mock():
    from app.infrastructure.notifications.email.email_notifier_base import EmailNotifierBase
    return AsyncMock(spec=EmailNotifierBase)


@pytest_asyncio.fixture
def ai_parser_mock():
    # If there is a base class for ai_parser, it should be used here.
    # For now, keeping it as a generic AsyncMock but better than nothing.
    return AsyncMock()


@pytest_asyncio.fixture
def email_validator_mock():
    return MagicMock(spec=EmailValidationService)


@pytest_asyncio.fixture
def notification_service_mock():
    return AsyncMock(spec=OfferNotificationService)


@pytest_asyncio.fixture
def service(
    offer_repo_mock,
    place_repo_mock,
    city_repo_mock,
    legal_role_repo_mock,
    ai_parser_mock,
    email_validator_mock,
    notification_service_mock,
):
    return OfferService(
        offer_repo=offer_repo_mock,
        place_repo=place_repo_mock,
        city_repo=city_repo_mock,
        legal_role_repo=legal_role_repo_mock,
        ai_parser=ai_parser_mock,
        email_validator=email_validator_mock,
        notification_service=notification_service_mock,
    )


@pytest.mark.asyncio
async def test_should_trigger_email_notification_when_offer_created(service, offer_repo_mock, email_validator_mock, notification_service_mock):
    # Given
    offer_add = OfferAdd(
        source=SourceType.USER,
        author="Test Author",
        email="test@example.com",
        description="Test Description",
        city_uuid=uuid4(),
        facility_uuid=uuid4(),
        roles_uuids=[uuid4()],
        date_str="2025-07-30",
        hour_str="10:00",
    )

    new_offer_mock = MagicMock(spec=Offer)
    offer_repo_mock.get_by_uuid.return_value = new_offer_mock
    email_validator_mock.should_send_user_offer_creation_email.return_value = True

    # When
    await service.create_offer(offer_add)

    # Then
    # Check repository calls
    assert offer_repo_mock.create.called

    # Check that it fetched the new offer to pass to validator
    offer_repo_mock.get_by_uuid.assert_called()

    # Check validator and notification calls
    email_validator_mock.should_send_user_offer_creation_email.assert_called_once_with(new_offer_mock)
    notification_service_mock.send_user_offer_created_email.assert_called_once_with(new_offer_mock)


@pytest.mark.asyncio
async def test_should_not_send_email_if_validator_returns_false_during_offer_creation(service, offer_repo_mock, email_validator_mock, notification_service_mock):
    # Given
    offer_add = OfferAdd(
        source=SourceType.USER,
        author="Test Author",
        email="test@example.com",
        description="Test Description",
        city_uuid=uuid4(),
        facility_uuid=uuid4(),
        roles_uuids=[uuid4()],
        date_str="2025-07-30",
        hour_str="10:00",
    )

    new_offer_mock = MagicMock(spec=Offer)
    offer_repo_mock.get_by_uuid.return_value = new_offer_mock
    email_validator_mock.should_send_user_offer_creation_email.return_value = False

    # When
    await service.create_offer(offer_add)

    # Then
    # Validator should be called, but notification service should not
    email_validator_mock.should_send_user_offer_creation_email.assert_called_once_with(new_offer_mock)
    notification_service_mock.send_user_offer_created_email.assert_not_called()


@pytest.mark.asyncio
async def test_should_set_valid_to_and_notify_slack_on_offer_creation(service, offer_repo_mock, city_repo_mock, notification_service_mock):
    city_uuid = uuid4()
    city_repo_mock.get_by_uuid.return_value = MagicMock(spec=City, id=12, lat=52.1, lon=21.0, name="City 12")

    offer_add = OfferAdd(
        author="Author",
        city_uuid=city_uuid,
        email="author@example.com",
        date="2025-01-02",
        hour="10:30",
        source=SourceType.USER,
    )

    await service.create_offer(offer_add)

    offer_repo_mock.create.assert_awaited_once()
    created_kwargs = offer_repo_mock.create.call_args.kwargs
    expected_valid_to = datetime(2025, 1, 2, 10, 30, tzinfo=ZoneInfo("Europe/Warsaw")).astimezone(ZoneInfo("UTC"))
    assert created_kwargs["valid_to"] == expected_valid_to
    assert created_kwargs["status"] == OfferStatus.ACTIVE
    assert created_kwargs["city_id"] == 12
    assert created_kwargs["lat"] == 52.1
    assert created_kwargs["lon"] == 21.0
    notification_service_mock.notify_new_offer_slack.assert_awaited_once()


@pytest.mark.asyncio
async def test_should_raise_404_when_creating_offer_with_missing_legal_roles(service, legal_role_repo_mock):
    role_uuid = uuid4()
    legal_role_repo_mock.get_by_uuids.return_value = []

    offer_add = OfferAdd(
        author="Author",
        city_uuid=uuid4(),
        email="author@example.com",
        roles=[role_uuid],
        source=SourceType.USER,
    )

    with pytest.raises(HTTPException) as exc:
        await service.create_offer(offer_add)

    assert exc.value.status_code == HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_should_default_valid_to_when_no_date_or_hour_provided(service, offer_repo_mock, city_repo_mock):
    city_repo_mock.get_by_uuid.return_value = MagicMock(spec=City, id=2, lat=50.0, lon=20.0, name="City 2")
    offer_add = OfferAdd(
        author="Author",
        city_uuid=uuid4(),
        email="author@example.com",
        source=SourceType.USER,
    )

    before_call = datetime.now(UTC)
    await service.create_offer(offer_add)
    after_call = datetime.now(UTC)

    created_kwargs = offer_repo_mock.create.call_args.kwargs
    assert before_call + timedelta(days=7) <= created_kwargs["valid_to"] <= after_call + timedelta(days=7)


@pytest.mark.asyncio
async def test_should_reject_offer_update_with_invalid_date(service, offer_repo_mock):
    offer_uuid = uuid4()
    db_offer = MagicMock(
        spec=Offer,
        id=1,
        uuid="offer-uuid",
        legal_roles=[],
        place=None,
        city=None,
        status=OfferStatus.NEW,
        email="old@example.com",
        source=SourceType.BOT,
    )
    offer_repo_mock.get_by_uuid.return_value = db_offer

    offer_update = OfferUpdate(date="2025-13-01")

    with pytest.raises(HTTPException) as exc:
        await service.update_offers(offer_uuid, offer_update)
    assert exc.value.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_should_raise_404_when_parsing_offer_without_raw_data(service, offer_repo_mock):
    offer_uuid = uuid4()
    offer_repo_mock.get_by_uuid.return_value = MagicMock(spec=Offer, raw_data=None)

    with pytest.raises(HTTPException) as exc:
        await service.parse_raw_offer(offer_uuid)
    assert exc.value.status_code == HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_should_skip_accepting_raw_offer_when_already_active(service, offer_repo_mock):
    offer_uuid = uuid4()
    offer_repo_mock.get_by_uuid.return_value = MagicMock(spec=Offer, id=1, status=OfferStatus.ACTIVE)

    await service.accept_raw_offer(offer_uuid)

    offer_repo_mock.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_send_email_on_offer_update_when_validator_allows(
    service,
    offer_repo_mock,
    legal_role_repo_mock,
    notification_service_mock,
    email_validator_mock,
):
    offer_uuid = uuid4()
    db_offer = MagicMock(
        spec=Offer,
        id=1,
        uuid="offer-uuid",
        legal_roles=[],
        place=None,
        city=None,
        status=OfferStatus.NEW,
        email="old@example.com",
        source=SourceType.BOT,
    )
    updated_offer = MagicMock(spec=Offer, email="new@example.com", author="Ann", status=OfferStatus.ACTIVE)
    offer_repo_mock.get_by_uuid.side_effect = [db_offer, updated_offer]
    legal_role_repo_mock.get_by_uuids.return_value = [MagicMock(spec=LegalRole, uuid=uuid4())]
    email_validator_mock.should_send_offer_email.return_value = True
    notification_service_mock.send_offer_imported_email.return_value = True

    offer_update = OfferUpdate(
        description="Updated",
        date="2025-02-02",
        hour="09:00",
        roles=[uuid4()],
        submit_email=True,
    )

    await service.update_offers(offer_uuid, offer_update)

    offer_repo_mock.update.assert_awaited_once()
    assert offer_repo_mock.update.call_args.args[0] == 1
    assert offer_repo_mock.update.call_args.kwargs["description"] == "Updated"
    assert db_offer.legal_roles == legal_role_repo_mock.get_by_uuids.return_value
    notification_service_mock.send_offer_imported_email.assert_awaited_once_with(
        updated_offer,
        "offer-uuid",
    )


@pytest.mark.asyncio
async def test_should_ignore_null_status_during_offer_update(service, offer_repo_mock):
    offer_uuid = uuid4()
    db_offer = MagicMock(
        spec=Offer,
        id=1,
        status=OfferStatus.NEW,
        legal_roles=[],
        place=None,
        city=None,
    )
    offer_repo_mock.get_by_uuid.return_value = db_offer

    # Pydantic model with status explicitly set to None
    offer_update = OfferUpdate(status=None, description="New Desc")

    await service.update_offers(offer_uuid, offer_update)

    # Check that status was NOT changed to None on the model
    assert db_offer.status == OfferStatus.NEW
    assert db_offer.description == "New Desc"
