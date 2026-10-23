# Substio API

[![Tests](https://github.com/mgurg/substio_app/actions/workflows/manual-tests.yml/badge.svg)](https://github.com/mgurg/substio_app/actions/workflows/manual-tests.yml)

Substio is a FastAPI backend for managing legal representation offers. It stores offers and locations, supports search by location and legal role, and can parse raw offers with AI before they are accepted or rejected.

## What it provides

- Offer creation, review, search, and similar-offer lookup
- City and facility lookup for location-based filtering
- Optional OpenAI parsing, email notifications, and Slack notifications
- PostgreSQL persistence with Alembic migrations

## Stack

Python 3.12+, FastAPI, SQLAlchemy 2.1 async, PostgreSQL, Alembic, Pydantic 2, uv, and pytest.

## Run locally

Docker and Docker Compose are required for the application and PostgreSQL. Copy the example environment file and set the database values for the Compose service:

```bash
cp app/.env.sample app/.env
```

Set `DB_HOST=db`, `DB_DATABASE=pg_db`, `DB_USERNAME=postgres`, and `DB_PASSWORD=postgres` in `app/.env`. Add API keys only for the integrations you intend to use. To enable the interactive API docs, set `APP_API_DOCS=/openapi.json`.

```bash
docker compose up --build -d
docker compose exec web .venv/bin/alembic upgrade head
curl http://localhost:5000/health
```

The health endpoint returns `{"status":"OK"}`. With OpenAPI enabled, the interactive docs are at `http://localhost:5000/docs`.

## API overview

| Route | Purpose |
| --- | --- |
| `GET /health` | Health check |
| `/offers` | Create, list, and search offers |
| `/offers/raw` | Review and parse incoming offers |
| `/places` | Look up cities and facilities |

Offer and place routes require an `Authorization: Bearer <token>` header. See the route definitions in [`app/controller/`](app/controller/) for available operations and parameters.

## Develop and test

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and make sure Docker is running. Integration tests use Testcontainers to start PostgreSQL.

```bash
uv sync --locked
uv run pytest -q
```

Run only tests that do not need Docker:

```bash
uv run pytest -m 'not integration' -q
```

Dependencies are declared in [`pyproject.toml`](pyproject.toml) and locked in [`uv.lock`](uv.lock). To refresh the lockfile, run `uv lock --upgrade`.

## Project layout

| Directory | Responsibility |
| --- | --- |
| `app/controller/` | HTTP routes |
| `app/services/` | Business logic |
| `app/repositories/` | Database queries |
| `app/database/models/` | SQLAlchemy models |
| `app/infrastructure/` | AI and notification integrations |
| `migrations/` | Alembic migrations |
| `tests/` | Unit and integration tests |
