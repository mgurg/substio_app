from pydantic import BaseModel
from typing import Any

class SubstitutionOffer(BaseModel):
    # Simplified version, I'll need more content for full accuracy
    description: str | None = None
    email: str | None = None

class UsageDetails(BaseModel):
    total_tokens: int

class ParseResponse(BaseModel):
    success: bool
    data: SubstitutionOffer | None = None
    error: str | None = None
    usage: UsageDetails | None = None
