import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

import app.services.offers.offer_import_service as offer_import_service_module
from app.database.models.enums import OfferStatus, SourceType
from app.database.models.models import City, LegalRole, Offer
from app.repositories.city_repo import CityRepo
from app.repositories.legal_role_repo import LegalRoleRepo
from app.repositories.offer_repo import OfferRepo
from app.repositories.place_repo import PlaceRepo
from app.schemas.domain.offer import FacebookPost, OfferAdd, OfferRawAdd, OfferUpdate
from app.services.email_validation_service import EmailValidationService
from app.services.offer_service import OfferService
from app.services.offers.offer_import_service import OfferImportService, parse_facebook_post_to_offer
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
    return AsyncMock()


@pytest_asyncio.fixture
def email_notifier_mock():
    return AsyncMock()


@pytest_asyncio.fixture
def ai_parser_mock():
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
    offer_import_service = OfferImportService(offer_repo=offer_repo_mock)
    return OfferService(
        offer_repo=offer_repo_mock,
        place_repo=place_repo_mock,
        city_repo=city_repo_mock,
        legal_role_repo=legal_role_repo_mock,
        ai_parser=ai_parser_mock,
        email_validator=email_validator_mock,
        offer_import_service=offer_import_service,
        notification_service=notification_service_mock,
    )


@pytest.mark.asyncio
async def test_create_offer_triggers_email_notification(service, offer_repo_mock, email_validator_mock, notification_service_mock):
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

    await service.create_offer(offer_add)

    # Check repository calls
    assert offer_repo_mock.create.called

    # Check that it fetched the new offer to pass to validator
    offer_repo_mock.get_by_uuid.assert_called()

    # Check validator and notification calls
    email_validator_mock.should_send_user_offer_creation_email.assert_called_once_with(new_offer_mock)
    notification_service_mock.send_user_offer_created_email.assert_called_once_with(new_offer_mock)


@pytest.mark.asyncio
async def test_create_offer_no_email_if_validator_returns_false(service, offer_repo_mock, email_validator_mock, notification_service_mock):
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

    await service.create_offer(offer_add)

    # Validator should be called, but notification service should not
    email_validator_mock.should_send_user_offer_creation_email.assert_called_once_with(new_offer_mock)
    notification_service_mock.send_user_offer_created_email.assert_not_called()


async def test_parse_facebook_post_to_offer_uses_filename_when_invalid_date():
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


class _UploadFileStub:
    def __init__(self, filename: str | None, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


@pytest.mark.asyncio
async def test_create_raw_offer_sets_email_and_status_new(service, offer_repo_mock, monkeypatch):
    monkeypatch.setattr(offer_import_service_module, "extract_and_fix_email", lambda _: "user@example.com")
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
    offer_repo_mock.get_by_offer_uid.return_value = MagicMock(spec=Offer)

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
async def test_create_offer_sets_valid_to_and_sends_slack(service, offer_repo_mock, city_repo_mock, notification_service_mock):
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
async def test_create_offer_defaults_valid_to_when_no_date_or_hour(service, offer_repo_mock, city_repo_mock):
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
async def test_import_raw_offers_rejects_non_json_extension(service):
    file = _UploadFileStub(filename="offers.txt", content=b"[]")
    with pytest.raises(HTTPException) as exc:
        await service.import_raw_offers(file)
    assert exc.value.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_import_raw_offers_rejects_invalid_json(service):
    file = _UploadFileStub(filename="offers.json", content=b"{not-json")
    with pytest.raises(HTTPException) as exc:
        await service.import_raw_offers(file)
    assert exc.value.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_import_raw_offers_rejects_non_list_json(service):
    file = _UploadFileStub(filename="offers.json", content=b'{"a":1}')
    with pytest.raises(HTTPException) as exc:
        await service.import_raw_offers(file)
    assert exc.value.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_import_raw_offers_handles_skips_and_conflicts(service, offer_repo_mock, monkeypatch):
    offer_repo_mock.get_by_offer_uid.return_value = None
    monkeypatch.setattr(offer_import_service_module, "extract_and_fix_email", lambda _: None)

    def _get_by_offer_uid_side_effect(offer_uid):
        if offer_uid == "dup":
            return MagicMock(spec=Offer)
        return None

    offer_repo_mock.get_by_offer_uid.side_effect = _get_by_offer_uid_side_effect
    posts = [
        {
            "User Name": "A",
            "User Profile URL": "u1",
            "Post URL": "dup",
            "Post Content": "content",
            "Date Posted": "2025-01-01T10:00:00",
        },
        {
            "User Name": "B",
            "User Profile URL": "u2",
            "Post URL": "u2",
            "Post Content": "nieaktualne offer",
            "Date Posted": "2025-01-02T10:00:00",
        },
        {
            "User Name": "C",
            "User Profile URL": "u3",
            "Post URL": "u3",
            "Post Content": "valid",
            "Date Posted": "2025-01-03T10:00:00",
        },
    ]
    file = _UploadFileStub(filename="offers.json", content=json.dumps(posts).encode("utf-8"))

    result = await service.import_raw_offers(file)

    assert result.total_records == 3
    assert result.imported_records == 1
    assert result.skipped_records == 2
    assert len(result.errors) == 2


@pytest.mark.asyncio
async def test_update_offers_rejects_invalid_date(service, offer_repo_mock):
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
async def test_parse_raw_offer_raises_when_no_raw_data(service, offer_repo_mock):
    offer_uuid = uuid4()
    offer_repo_mock.get_by_uuid.return_value = MagicMock(spec=Offer, raw_data=None)

    with pytest.raises(HTTPException) as exc:
        await service.parse_raw_offer(offer_uuid)
    assert exc.value.status_code == HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_accept_raw_offer_skips_when_active(service, offer_repo_mock):
    offer_uuid = uuid4()
    offer_repo_mock.get_by_uuid.return_value = MagicMock(spec=Offer, id=1, status=OfferStatus.ACTIVE)

    await service.accept_raw_offer(offer_uuid)

    offer_repo_mock.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_offers_sends_email_when_validator_allows(
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
async def test_update_offers_ignores_null_status(service, offer_repo_mock):
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
