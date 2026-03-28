import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from starlette.status import HTTP_409_CONFLICT

from app.database.models.enums import OfferStatus, SourceType
from app.database.models.models import Offer
from app.repositories.offer_repo import OfferRepo
from app.schemas.domain.offer import FacebookPost, OfferRawAdd
from app.services.offers.offer_import_service import OfferImportService, parse_facebook_post_to_offer


class _UploadFileStub:
    def __init__(self, filename: str | None, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


@pytest.fixture
def offer_repo_mock():
    return AsyncMock(spec=OfferRepo)


@pytest.fixture
def import_service(offer_repo_mock):
    return OfferImportService(offer_repo=offer_repo_mock)


def test_parse_facebook_post_to_offer_success():
    # Given
    post = FacebookPost(
        user_name="Test User",
        user_profile_url="https://fb.com/user",
        post_url="https://fb.com/post",
        post_content="Content",
        date_posted="2025-01-01T10:00:00",
    )

    # When
    offer = parse_facebook_post_to_offer(post, None)

    # Then
    assert offer.author == "Test User"
    assert offer.timestamp == datetime.fromisoformat("2025-01-01T10:00:00")
    assert offer.source == SourceType.BOT


def test_parse_facebook_post_to_offer_uses_filename_fallback():
    # Given
    post = FacebookPost(
        user_name="Test User",
        user_profile_url="u",
        post_url="p",
        post_content="c",
        date_posted=None,
    )
    # filename with timestamp 20250819_110812

    # When
    offer = parse_facebook_post_to_offer(post, "20250819_110812.json")

    # Then
    assert offer.timestamp == datetime(2025, 8, 19, 11, 8, 12)


@pytest.mark.asyncio
async def test_create_raw_offer_sets_email_and_status_new(import_service, offer_repo_mock, monkeypatch):
    from app.services.offers import offer_import_service as offer_import_service_module
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

    await import_service.create_raw_offer(offer)

    offer_repo_mock.create.assert_awaited_once()
    created_kwargs = offer_repo_mock.create.call_args.kwargs
    assert created_kwargs["email"] == "user@example.com"
    assert created_kwargs["status"] == OfferStatus.NEW


@pytest.mark.asyncio
async def test_create_raw_offer_duplicate(import_service, offer_repo_mock):
    # Given
    offer_repo_mock.get_by_offer_uid.return_value = MagicMock(spec=Offer)
    offer = OfferRawAdd(
        raw_data="data",
        author="Author",
        author_uid="auid",
        offer_uid="ouid",
        timestamp=datetime.now(UTC),
        source=SourceType.BOT,
    )

    # When & Then
    with pytest.raises(HTTPException) as exc:
        await import_service.create_raw_offer(offer)
    assert exc.value.status_code == HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_import_raw_offers_invalid_extension(import_service):
    # Given
    file = _UploadFileStub(filename="test.txt", content=b"[]")

    # When & Then
    with pytest.raises(HTTPException) as exc:
        await import_service.import_raw_offers(file)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_import_raw_offers_full_flow(import_service, offer_repo_mock):
    # Given
    posts = [
        {
            "User Name": "User 1",
            "User Profile URL": "u1",
            "Post URL": "p1",
            "Post Content": "content 1",
            "Date Posted": "2025-01-01T10:00:00",
        },
        {
            "User Name": "User 2",
            "User Profile URL": "u2",
            "Post URL": "p2",
            "Post Content": "nieaktualne content",
            "Date Posted": "2025-01-01T10:00:00",
        }
    ]
    file = _UploadFileStub(filename="data.json", content=json.dumps(posts).encode("utf-8"))
    offer_repo_mock.get_by_offer_uid.return_value = None

    # When
    result = await import_service.import_raw_offers(file)

    # Then
    assert result.total_records == 2
    assert result.imported_records == 1
    assert result.skipped_records == 1
    offer_repo_mock.create.assert_awaited_once()


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
async def test_import_raw_offers_rejects_invalid_json(import_service):
    file = _UploadFileStub(filename="offers.json", content=b"{not-json")
    with pytest.raises(HTTPException) as exc:
        await import_service.import_raw_offers(file)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_import_raw_offers_rejects_non_list_json(import_service):
    file = _UploadFileStub(filename="offers.json", content=b'{"a":1}')
    with pytest.raises(HTTPException) as exc:
        await import_service.import_raw_offers(file)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_import_raw_offers_handles_skips_and_conflicts(import_service, offer_repo_mock, monkeypatch):
    from app.services.offers import offer_import_service as offer_import_service_module
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

    result = await import_service.import_raw_offers(file)

    assert result.total_records == 3
    assert result.imported_records == 1
    assert result.skipped_records == 2
    assert len(result.errors) == 2
