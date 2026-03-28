import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.models import LegalRole
from app.repositories.generics import GenericRepo


@pytest.fixture
async def db_session(client) -> AsyncSession:
    # client fixture in conftest.py already sets up the app and DB
    from app.core.database import get_db
    async for session in get_db():
        yield session


@pytest.mark.asyncio
@pytest.mark.integration
async def test_generic_repo_operations(db_session: AsyncSession):
    # Given
    repo = GenericRepo(db_session, LegalRole)
    role_uuid = uuid.uuid4()

    # When
    # Test create
    role = await repo.create(uuid=role_uuid, name="Test Role", symbol="TR")
    # Test get_by_id
    fetched = await repo.get_by_id(role.id)
    # Test update
    await repo.update(role.id, name="Updated Role")
    updated = await repo.get_by_id(role.id)
    # Test filter
    results = await repo.filter(name="Updated Role")
    # Test get_all
    all_roles = await repo.get_all()

    # Then
    assert role.id is not None
    assert fetched is not None
    assert fetched.uuid == role_uuid
    assert updated.name == "Updated Role"
    assert len(results) == 1
    assert results[0].id == role.id
    assert len(all_roles) >= 1

    # When (Bulk Create)
    # Test create_all
    new_uuid1 = uuid.uuid4()
    new_uuid2 = uuid.uuid4()
    await repo.create_all([
        {"uuid": new_uuid1, "name": "Bulk 1", "symbol": "B1"},
        {"uuid": new_uuid2, "name": "Bulk 2", "symbol": "B2"}
    ])
    bulk1 = await repo.filter(name="Bulk 1")

    # Then
    assert len(bulk1) == 1

    # When (Delete)
    # Test delete
    deleted = await repo.delete(role.id)
    none_deleted = await repo.delete(999999)

    # Then
    assert deleted is not None
    assert deleted.id == role.id
    assert none_deleted is None
