from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from fastapi import HTTPException
from starlette.status import HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

import app.service.OfferService as offer_service_module
from app.database.models.enums import OfferStatus, SourceType
from app.schemas.rest.requests import FacebookPost, OfferAdd, OfferRawAdd, OfferUpdate
from app.service.OfferService import OfferService, parse_facebook_post_to_offer


@pytest_asyncio.fixture
def offer_repo_mock():
    return AsyncMock()


@pytest_asyncio.fixture
def place_repo_mock():
    return AsyncMock()


@pytest_asyncio.fixture
def city_repo_mock():
    return AsyncMock()


@pytest_asyncio.fixture
def legal_role_repo_mock():
    return AsyncMock()


@pytest_asyncio.fixture
def slack_notifier_mock():
    return AsyncMock()


@pytest_asyncio.fixture
def email_notifier_mock():
    return AsyncMock()


@pytest_asyncio.fixture
def ai_parser_mock():
    return AsyncMock()


@pytest_asyncio.fixture
def email_validator_mock():
    return Mock()


@pytest_asyncio.fixture
def service(
    offer_repo_mock,
    place_repo_mock,
    city_repo_mock,
    legal_role_repo_mock,
    slack_notifier_mock,
    email_notifier_mock,
    ai_parser_mock,
    email_validator_mock,
):
    return OfferService(
        offer_repo=offer_repo_mock,
        place_repo=place_repo_mock,
        city_repo=city_repo_mock,
        legal_role_repo=legal_role_repo_mock,
        slack_notifier=slack_notifier_mock,
        email_notifier=email_notifier_mock,
        ai_parser=ai_parser_mock,
        email_validator=email_validator_mock,
    )


def test_parse_facebook_post_to_offer_uses_filename_when_invalid_date():
    post = FacebookPost(
        user_name="Test User",
        user_profile_url="https://example.com/user",
        post_url="https://example.com/post",
        post_content="Content",
        date_posted="not-a-date",
    )

    offer = parse_facebook_post_to_offer(post, "20250819_110812.json")

    assert offer.timestamp == datetime(2025, 8, 19, 11, 8, 12)
    assert offer.source == SourceType.BOT
    assert offer.author == "Test User"


@pytest.mark.asyncio
async def test_create_raw_offer_sets_email_and_status_new(service, offer_repo_mock, monkeypatch):
    monkeypatch.setattr(offer_service_module, "extract_and_fix_email", lambda _: "user@example.com")
    offer_repo_mock.get_by_offer_uid.return_value = None

    offer = OfferRawAdd(
        raw_data="Contact me at user@example.com",
        author="Author",
        author_uid="author-uid",
        offer_uid="offer-uid",
        timestamp=datetime.now(UTC),
        source=SourceType.BOT,
    )

    await service.create_raw_offer(offer)

    offer_repo_mock.create.assert_awaited_once()
    created_kwargs = offer_repo_mock.create.call_args.kwargs
    assert created_kwargs["email"] == "user@example.com"
    assert created_kwargs["status"] == OfferStatus.NEW


@pytest.mark.asyncio
async def test_create_raw_offer_duplicate_raises_conflict(service, offer_repo_mock):
    offer_repo_mock.get_by_offer_uid.return_value = SimpleNamespace()

    offer = OfferRawAdd(
        raw_data="data",
        author="Author",
        author_uid="author-uid",
        offer_uid="offer-uid",
        timestamp=datetime.now(UTC),
        source=SourceType.BOT,
    )

    with pytest.raises(HTTPException) as exc:
        await service.create_raw_offer(offer)

    assert exc.value.status_code == HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_create_offer_sets_valid_to_and_sends_slack(service, offer_repo_mock, city_repo_mock, slack_notifier_mock):
    city_uuid = uuid4()
    city_repo_mock.get_by_uuid.return_value = SimpleNamespace(id=12, lat=52.1, lon=21.0)

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
    expected_valid_to = datetime(2025, 1, 2, 10, 30, tzinfo=ZoneInfo("Europe/Warsaw")).astimezone(
        ZoneInfo("UTC")
    )
    assert created_kwargs["valid_to"] == expected_valid_to
    assert created_kwargs["status"] == OfferStatus.ACTIVE
    assert created_kwargs["city_id"] == 12
    assert created_kwargs["lat"] == 52.1
    assert created_kwargs["lon"] == 21.0
    slack_notifier_mock.send_new_offer_notification.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_offer_raises_when_legal_roles_missing(service, legal_role_repo_mock):
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
async def test_update_offers_sends_email_when_validator_allows(
    service,
    offer_repo_mock,
    legal_role_repo_mock,
    email_notifier_mock,
    email_validator_mock,
):
    offer_uuid = uuid4()
    db_offer = SimpleNamespace(
        id=1,
        uuid="offer-uuid",
        legal_roles=[],
        place=None,
        city=None,
        status=OfferStatus.NEW,
        email="old@example.com",
        source=SourceType.BOT,
    )
    updated_offer = SimpleNamespace(email="new@example.com", author="Ann", status=OfferStatus.ACTIVE)
    offer_repo_mock.get_by_uuid.side_effect = [db_offer, updated_offer]
    legal_role_repo_mock.get_by_uuids.return_value = [SimpleNamespace(uuid=uuid4())]
    email_validator_mock.should_send_offer_email.return_value = True
    email_notifier_mock.send_offer_imported_email.return_value = True

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
    email_notifier_mock.send_offer_imported_email.assert_awaited_once_with(
        recipient_email="new@example.com",
        recipient_name="Ann",
        offer_uuid="offer-uuid",
    )
