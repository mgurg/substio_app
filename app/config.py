import os
from functools import lru_cache
from pathlib import Path

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(__file__).parent.parent / "app"


class Settings(BaseSettings):
    PROJECT_DIR: os.PathLike[str] = Path(__file__).parent.parent

    DB_POSTGRES_URL: PostgresDsn = "postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}".format(
        DB_USER=os.getenv("DB_USERNAME"),
        DB_PASSWORD=os.getenv("DB_PASSWORD"),
        DB_HOST=os.getenv("DB_HOST"),
        DB_NAME=os.getenv("DB_DATABASE"),
    )

    model_config = SettingsConfigDict(
        env_prefix="", env_file_encoding="utf-8", env_file=f"{APP_DIR}/.env", extra="allow"
    )


@lru_cache
def get_settings() -> BaseSettings:
    # path = Path(__file__).parent.parent / "app" / ".env.testing"
    # return Settings(_env_file=path.as_posix(), _env_file_encoding="utf-8")
    return Settings()
