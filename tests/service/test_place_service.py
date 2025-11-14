# tests/service/test_place_service.py
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio

from app.database.models.enums import PlaceCategory
from app.exceptions import ConflictError, NotFoundError
from app.schemas.rest.requests import PlaceAdd
from app.service.PlaceService import PlaceService


@pytest_asyncio.fixture
def city_repo_mock():
    return AsyncMock()


@pytest_asyncio.fixture
def place_repo_mock():
    return AsyncMock()


@pytest_asyncio.fixture
def service(city_repo_mock, place_repo_mock):
    return PlaceService(city_repo=city_repo_mock, place_repo=place_repo_mock)


@pytest.mark.asyncio
async def test_get_place_by_uuid_found(service, place_repo_mock):
    place_uuid = uuid4()
    fake_place = {"uuid": str(place_uuid), "name": "Test Place"}
    place_repo_mock.get_by_uuid.return_value = fake_place

    result = await service.get_place_by_uuid(place_uuid)

    assert result == fake_place
    place_repo_mock.get_by_uuid.assert_awaited_once_with(place_uuid)


@pytest.mark.asyncio
async def test_get_place_by_uuid_not_found(service, place_repo_mock):
    place_repo_mock.get_by_uuid.return_value = None
    with pytest.raises(NotFoundError):
        await service.get_place_by_uuid(uuid4())


@pytest.mark.asyncio
async def test_create_place_conflict(service, place_repo_mock):
    place_add = PlaceAdd(
        name="Sąd rejonowy",
        type="SR",
        street="Main 12",
        city="Warsaw",
        category=PlaceCategory.COURT,
        postal_code="00-001",
        department=None,
        street_name=None,
        street_number=None,
        lat=52.0,
        lon=21.0,
    )

    # ✅ Return something with a .uuid attribute (like ORM model would)
    place_repo_mock.get_by_name_and_distance.return_value = [
        SimpleNamespace(uuid=uuid4())
    ]

    with pytest.raises(ConflictError):
        await service.create(place_add)


@pytest.mark.asyncio
async def test_create_place_success(service, place_repo_mock):
    place_add = PlaceAdd(
        name="New Room", type="room", street="Main 12", city="Warsaw",
        category=PlaceCategory.COURT, postal_code="00-001", department=None,
        street_name=None, street_number=None, lat=52.0, lon=21.0
    )
    place_repo_mock.get_by_name_and_distance.return_value = []
    place_repo_mock.create.return_value = None

    await service.create(place_add)

    place_repo_mock.create.assert_awaited_once()
