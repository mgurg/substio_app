import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.database.models.enums import PlaceCategory
from app.database.models.models import Place
from app.repositories.place_repo import PlaceRepo


@pytest.fixture
async def db_session(client) -> AsyncSession:
    from app.core.database import _init_engine_if_needed, get_db
    _init_engine_if_needed()
    async for session in get_db():
        yield session


@pytest.mark.asyncio
@pytest.mark.integration
async def test_should_perform_place_repo_operations(db_session: AsyncSession):
    # Given
    repo = PlaceRepo(db_session)
    place_uuid = uuid.uuid4()
    place = Place(
        uuid=place_uuid,
        name="Test Hospital",
        name_ascii="test hospital",
        city="Warszawa",
        category=PlaceCategory.OTHER,
        type="hospital",
        lat=52.2297,
        lon=21.0122
    )
    db_session.add(place)
    await db_session.commit()

    # When
    # 1. Test get_by_uuid success
    fetched = await repo.get_by_uuid(place_uuid)
    # 3. Test get_by_partial_name
    results = await repo.get_by_partial_name("test", place_type="hospital")
    # 4. Test get_by_name_and_distance
    # Same location
    nearby = await repo.get_by_name_and_distance("Test Hospital", 52.2297, 21.0122)
    # Far away
    far_away = await repo.get_by_name_and_distance("Test Hospital", 50.0, 20.0)

    # Then
    assert fetched.name == "Test Hospital"
    assert len(results) >= 1
    assert results[0].name == "Test Hospital"
    assert len(nearby) == 1
    assert len(far_away) == 0

    # When & Then (failure)
    # 2. Test get_by_uuid failure
    with pytest.raises(NotFoundError):
        await repo.get_by_uuid(uuid.uuid4())
