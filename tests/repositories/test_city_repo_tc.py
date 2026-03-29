import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.database.models.models import City
from app.repositories.city_repo import CityRepo


@pytest.fixture
async def db_session(client) -> AsyncSession:
    from app.core.database import get_db
    async for session in get_db():
        yield session


@pytest.mark.asyncio
@pytest.mark.integration
async def test_should_perform_city_repo_operations(db_session: AsyncSession):
    # Given
    repo = CityRepo(db_session)
    city_uuid = uuid.uuid4()
    city = City(
        uuid=city_uuid,
        name="Warszawa",
        name_ascii="warszawa",
        importance=1.0,
        category="city",
        teryt_simc="12345"
    )
    db_session.add(city)
    await db_session.commit()

    # When
    # Test get_by_uuid success
    fetched = await repo.get_by_uuid(city_uuid)
    # Test find_by_teryt
    found = await repo.find_by_teryt("12345")
    # Test get_by_partial_name
    results = await repo.get_by_partial_name("warsz")

    # Then
    assert fetched.name == "Warszawa"
    assert found.uuid == city_uuid
    assert len(results) >= 1
    assert results[0].name == "Warszawa"

    # When & Then (failure cases)
    # Test get_by_uuid failure
    with pytest.raises(NotFoundError):
        await repo.get_by_uuid(uuid.uuid4())

    # Test find_by_teryt failure
    not_found = await repo.find_by_teryt("nonexistent")
    assert not_found is None
