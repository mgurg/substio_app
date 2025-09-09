from typing import Literal

from loguru import logger
from pydantic import BaseModel, EmailStr, field_validator


class SubstitutionOffer(BaseModel):
    location: Literal["sąd", "policja", "prokuratura"] | None = None
    location_full_name: str | None = None
    date: list[str] | None = None
    time: list[str] | None = None
    description: str | None = None
    legal_roles: list[Literal["adwokat", "radca prawny", "aplikant adwokacki", "aplikant radcowski"]] | None = None
    email: EmailStr | None = None

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v):
        """Validate email and set to None if invalid format."""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            v = v.strip().replace(" ", "")
            if "@" not in v or "." not in v:
                logger.warning(f"Invalid email format detected (no @ sign or dot): {v}, setting to None")
                return None
            parts = v.split("@")
            if len(parts) != 2 or not parts[0] or not parts[1]:
                logger.warning(f"Invalid email format detected: {v}, setting to None")
                return None
        return v


class UsageDetails(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    elapsed_time: float


class ParseResponse(BaseModel):
    success: bool
    data: SubstitutionOffer | None = None
    error: str | None = None
    usage: UsageDetails | None = None
