import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.models import LegalRole
from app.repositories.generics import GenericRepo


@pytest.fixture
async def db_session(client) -> AsyncSession:
    # client fixture in conftest.py already sets up the app and DB
    from app.core.database import _init_engine_if_needed, async_session
    _init_engine_if_needed()
    async with async_session() as session:
        yield session


@pytest.mark.asyncio
@pytest.mark.integration
async def test_generic_repo_operations(db_session: AsyncSession):
    repo = GenericRepo(db_session, LegalRole)

    # Test create
    role_uuid = uuid.uuid4()
    role = await repo.create(uuid=role_uuid, name="Test Role", symbol="TR")
    assert role.id is not None
    assert role.name == "Test Role"

    # Test get_by_id
    fetched = await repo.get_by_id(role.id)
    assert fetched is not None
    assert fetched.uuid == role_uuid

    # Test update
    await repo.update(role.id, name="Updated Role")
    updated = await repo.get_by_id(role.id)
    assert updated.name == "Updated Role"

    # Test filter
    results = await repo.filter(name="Updated Role")
    assert len(results) == 1
    assert results[0].id == role.id

    # Test get_all
    all_roles = await repo.get_all()
    assert len(all_roles) >= 1

    # Test create_all
    new_uuid1 = uuid.uuid4()
    new_uuid2 = uuid.uuid4()
    await repo.create_all([
        {"uuid": new_uuid1, "name": "Bulk 1", "symbol": "B1"},
        {"uuid": new_uuid2, "name": "Bulk 2", "symbol": "B2"}
    ])
    bulk1 = await repo.filter(name="Bulk 1")
    assert len(bulk1) == 1

    # Test delete
    deleted = await repo.delete(role.id)
    assert deleted is not None
    assert deleted.id == role.id

    none_deleted = await repo.delete(999999)
    assert none_deleted is None
