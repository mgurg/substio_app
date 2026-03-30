# Agent Instructions

### For AI Agents

When working on this codebase:

1. **Always use `uv`** instead of `pip` or `python -m venv`.
2. **Use `uv run`** to execute Python scripts (no activation needed).
3. **Use `pytest`** for running tests; note that some tests use `Testcontainers` (PostgreSQL), which requires Docker.

## Project Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Async)
- **Database**: [SQLAlchemy 2.0](https://docs.sqlalchemy.org/) (Async) with [Alembic](https://alembic.sqlalchemy.org/) for migrations
- **Validation**: [Pydantic 2](https://docs.pydantic.dev/) for schemas
- **Testing**: [Pytest](https://docs.pytest.org/) with [Testcontainers](https://testcontainers-python.readthedocs.io/)
- **Dependencies**: Managed via `pyproject.toml` and `uv.lock`

## Project Architecture

Follow the standard Layered Architecture:

- **`app/controller/`**: FastAPI routers. Handle HTTP requests, input validation (Pydantic), and return serialized responses.
- **`app/services/`**: Core business logic. Orchestrate calls to multiple repositories and external services.
- **`app/repositories/`**: Data access layer. Use `GenericRepo` for CRUD and specialized repositories for complex queries.
- **`app/database/models/`**: SQLAlchemy models.
- **`app/schemas/domain/`**: Pydantic models for data transfer between layers and API responses.

## Coding Conventions

- **Context First**: Study related code before making changes to fully **understand the context**.
- **Simplicity**: Try to **remove all unavoidable complexity** from the task before you start coding. **Ask challenging questions if needed** to simplify solutions.
- **DRY & Modular**: Write clean, modular, readable code. Use `GenericRepo` where possible to avoid duplication.
- **Dependency Injection**: Prefer composition and dependency injection (FastAPI `Depends`).
- **UUIDs**: Use `uuid` columns for public identification (API endpoints) and `id` (integer) for internal database primary keys and relations.
- **Async/Await**: This is an async codebase. Ensure you use `await` for database calls and other I/O.
- **Zen of Python**: Remember and follow the **Zen of Python**.

## Testing

- New features should include appropriate tests in the `tests/` directory.
- Use `conftest.py` for shared fixtures.
- API and Repository tests often require a running database (handled automatically via `Testcontainers` in `tests/conftest.py`).

### Testing Standards
- **Naming Convention**:
    - Unit tests (no database required): `test_*.py`
    - Integration tests (database/Testcontainers required): `test_*_tc.py`
- **Markers**:
    - All tests requiring a database MUST be marked with `@pytest.mark.integration`.
    - Async tests MUST be marked with `@pytest.mark.asyncio`.
- **Fixtures**:
    - Use the `client` fixture for API tests.
    - Use the `db_session` fixture for Repository tests.
- **Location**:
    - `tests/api/`: Controller/Route tests.
    - `tests/services/`: Business logic tests (prefer unit tests with mocks).
    - `tests/repositories/`: Data access tests (usually integration tests with `_tc.py`).
    - `tests/infrastructure/`: External service integrations.