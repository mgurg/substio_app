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
async def test_create_raw_offer_success(import_service, offer_repo_mock):
    # Given
    offer_repo_mock.get_by_offer_uid.return_value = None
    offer = OfferRawAdd(
        raw_data="Contact me at test@example.com",
        author="Author",
        author_uid="auid",
        offer_uid="ouid",
        timestamp=datetime.now(UTC),
        source=SourceType.BOT,
    )

    # When
    await import_service.create_raw_offer(offer)

    # Then
    offer_repo_mock.create.assert_awaited_once()
    args = offer_repo_mock.create.call_args.kwargs
    assert args["email"] == "test@example.com"
    assert args["status"] == OfferStatus.NEW


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
