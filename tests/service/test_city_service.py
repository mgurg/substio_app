from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio

from app.core.exceptions import NotFoundError
from app.service.CityService import CityService


@pytest_asyncio.fixture
def city_repo_mock():
    return AsyncMock()


@pytest_asyncio.fixture
def service(city_repo_mock):
    return CityService(city_repo=city_repo_mock)


@pytest.mark.asyncio
async def test_get_city_by_uuid_returns_city(service, city_repo_mock):
    city_uuid = uuid4()
    fake_city = SimpleNamespace(uuid=city_uuid, name="Test City")
    city_repo_mock.get_by_uuid.return_value = fake_city

    result = await service.get_city_by_uuid(city_uuid)

    assert result == fake_city
    city_repo_mock.get_by_uuid.assert_awaited_once_with(city_uuid)


@pytest.mark.asyncio
async def test_get_city_by_uuid_propagates_not_found(service, city_repo_mock):
    city_uuid = uuid4()
    city_repo_mock.get_by_uuid.side_effect = NotFoundError("City", str(city_uuid))

    with pytest.raises(NotFoundError):
        await service.get_city_by_uuid(city_uuid)
