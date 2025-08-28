import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(__file__).parent.parent / "app"


class Settings(BaseSettings):
    APP_DEBUG: bool = False
    APP_ENV: Literal["DEV", "PROD"]
    APP_URL: str
    APP_API_DOCS: str | None = os.getenv("APP_API_DOCS")
    PROJECT_DIR: os.PathLike[str] = Path(__file__).parent.parent

    DB_POSTGRES_URL: PostgresDsn = PostgresDsn.build(
        scheme="postgresql+psycopg",
        username=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")) if os.getenv("DB_PORT") else None,
        path=os.getenv("DB_DATABASE"),
    )

    API_KEY_OPENAI: str | None = os.getenv("API_KEY_OPENAI")
    OPENAI_MODEL: str = "gpt-5-nano"

    SENTRY_DSN: str | None = os.getenv("SENTRY_DSN")
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL")

    SYSTEM_PROMPT: str = """
    Z podanego opisu zastępstwa procesowego wyodrębnij następujące informacje:

    - `location`: Typ instytucji – wybierz jedną z: "sąd" (SR,SO,SA), "policja" (MPP,KMP), "prokuratura". Ustaw `null`, jeśli nie można określić.
    - `location_full_name`: Pełna nazwa instytucji, np. "Sąd Rejonowy dla Warszawy-Mokotowa", lub `null`.
    - `date`: Lista dat zastępstwa w formacie **RRRR-MM-DD (np. 2025-07-30)**. Jeśli podana jest tylko jedna, zwróć listę z jednym elementem. Jeśli brak – `null`.
    - `time`: Lista godzin zastępstwa w formacie  **HH:MM** (24-godzinny format, np. 13:45). Jeśli brak – `null`.
    - `description`: Krótkie streszczenie charakteru sprawy lub kontekstu. **Usuń email** jeżeli występuje.
    - `legal_roles`: Lista grup docelowych – wybierz spośród: "adwokat", "radca prawny", "aplikant adwokacki", "aplikant radcowski". Jeśli brak informacji – `null`.
    - `email`: Adres e-mail, jeśli występuje w opisie. Jeśli nie ma – `null`.

    Zwróć dane w formacie JSON zgodnym ze schematem.
    """

    model_config = SettingsConfigDict(
        env_prefix="", env_file_encoding="utf-8", env_file=f"{APP_DIR}/.env", extra="allow"
    )


@lru_cache
def get_settings() -> BaseSettings:
    return Settings()
