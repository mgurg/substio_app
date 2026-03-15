
from pydantic import BaseModel


class SubstitutionOffer(BaseModel):
    # Simplified version, I'll need more content for full accuracy
    description: str | None = None
    email: str | None = None


class UsageDetails(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    elapsed_time: float



class ParseResponse(BaseModel):
    success: bool
    data: SubstitutionOffer | None = None
    error: str | None = None
    usage: UsageDetails | None = None
