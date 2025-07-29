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

    API_KEY_OPENAI: str = os.getenv("API_KEY_OPENAI")
    OPENAI_MODEL: str = "gpt-4.1-nano"

    SYSTEM_PROMPT: str = """
    Z podanego opisu zastępstwa procesowego wyodrębnij następujące informacje:

    - `location`: Typ instytucji – wybierz jedną z: "sąd" (SR,SO,SA), "policja" (MPP,KMP), "prokuratura". Ustaw `null`, jeśli nie można określić.
    - `location_full_name`: Pełna nazwa instytucji, np. "Sąd Rejonowy dla Warszawy-Mokotowa", lub `null`.
    - `date`: Lista dat zastępstwa w formacie **RRRR-MM-DD (np. 2025-07-30)**. Jeśli podana jest tylko jedna, zwróć listę z jednym elementem. Jeśli brak – `null`.
    - `time`: Lista godzin zastępstwa w formacie  **HH:MM** (24-godzinny format, np. 13:45). Jeśli brak – `null`.
    - `description`: Krótkie streszczenie charakteru sprawy lub kontekstu. **Usuń email** jeżeli występuje.
    - `target_audience`: Lista grup docelowych – wybierz spośród: "adwokat", "radca prawny", "aplikant adwokacki", "aplikant radcowski". Jeśli brak informacji – `null`.
    - `email`: Adres e-mail, jeśli występuje w opisie. Jeśli nie ma – `null`.

    Zwróć dane w formacie JSON zgodnym ze schematem.
    """

    model_config = SettingsConfigDict(
        env_prefix="", env_file_encoding="utf-8", env_file=f"{APP_DIR}/.env", extra="allow"
    )


@lru_cache
def get_settings() -> BaseSettings:
    # path = Path(__file__).parent.parent / "app" / ".env.testing"
    # return Settings(_env_file=path.as_posix(), _env_file_encoding="utf-8")
    return Settings()
