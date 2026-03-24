import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.database.models.models import City
from app.repositories.city_repo import CityRepo


@pytest.fixture
async def db_session(client) -> AsyncSession:
    from app.core.database import _init_engine_if_needed, async_session
    _init_engine_if_needed()
    async with async_session() as session:
        yield session


@pytest.mark.asyncio
@pytest.mark.integration
async def test_city_repo_operations(db_session: AsyncSession):
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

    # Test get_by_uuid success
    fetched = await repo.get_by_uuid(city_uuid)
    assert fetched.name == "Warszawa"

    # Test get_by_uuid failure
    with pytest.raises(NotFoundError):
        await repo.get_by_uuid(uuid.uuid4())

    # Test find_by_teryt
    found = await repo.find_by_teryt("12345")
    assert found.uuid == city_uuid

    not_found = await repo.find_by_teryt("nonexistent")
    assert not_found is None

    # Test get_by_partial_name
    results = await repo.get_by_partial_name("warsz")
    assert len(results) >= 1
    assert results[0].name == "Warszawa"
