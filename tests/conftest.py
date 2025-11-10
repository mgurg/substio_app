import contextlib
import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

# Ensure project root is on sys.path for `import app`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def postgres_url_env() -> Generator[dict, None, None]:
    """Start a Postgres testcontainer and expose env vars required by the app.

    Yields a dict with env mapping to restore later.
    """
    with PostgresContainer("postgres:17-alpine") as pg:
        host = pg.get_container_host_ip()
        port = pg.get_exposed_port(5432)
        user = pg.username
        password = pg.password
        db = pg.dbname

        # Prepare environment variables as expected by app.config.Settings
        env = {
            "DB_USERNAME": user,
            "DB_PASSWORD": password,
            "DB_HOST": host,
            "DB_PORT": str(port),
            "DB_DATABASE": db,  # pydantic will handle leading slash
            # Optional: prevent OpenAI usage during tests
            "API_KEY_OPENAI": "",
            # Provide dummy API keys to prevent external clients from initializing with real network calls
            "API_KEY_MAILERSEND": "test_dummy_key",
            "MAILERSEND_API_KEY": "test_dummy_key",
            # Ensure we are not in PROD to disable prod-only integrations like Sentry
            "APP_ENV": "DEV",
            # Required app settings for Settings() validation
            "APP_URL": "http://testserver",
            "APP_DOMAIN": "test.local",
            "APP_ADMIN_MAIL": "admin@test.local",
            "SLACK_WEBHOOK_URL": "http://localhost/fake-webhook",
            "APP_API_DOCS": "/openapi.json",
        }

        # Backup old environment values and set new ones
        old_env = {k: os.environ.get(k) for k in env}
        try:
            os.environ.update(env)
            yield env
        finally:
            # Restore previous env
            for k, v in old_env.items():
                if v is None:
                    with contextlib.suppress(KeyError):
                        del os.environ[k]
                else:
                    os.environ[k] = v


@pytest.fixture(scope="session")
def apply_migrations(postgres_url_env) -> None:
    """Run Alembic migrations against the container DB."""
    # Clear cached settings so alembic.env picks up new URL built from env
    from app.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    # Use repository's alembic.ini with absolute path to tolerate IDE CWD set to tests/
    alembic_ini = PROJECT_ROOT / "alembic.ini"
    cfg = AlembicConfig(str(alembic_ini))
    # Ensure script_location resolves to the absolute migrations directory
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def app(apply_migrations):
    # Now import the app after env and migrations are ready
    from app.main import create_application

    return create_application()


@pytest.fixture()
def client(app) -> Generator[TestClient, None, None]:
    headers = {"Authorization": "Bearer " + ("a" * 31)}
    with TestClient(app, base_url="http://testserver") as c:
        # Set default headers without using deprecated constructor args
        c.headers.update(headers)
        yield c
