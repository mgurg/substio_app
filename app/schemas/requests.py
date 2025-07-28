from datetime import datetime

from pydantic import BaseModel

from app.database.models.enums import SourceType


class OfferAdd(BaseModel):
    raw_data: str
    author: str
    author_uid: str
    offer_uid: str
    timestamp: datetime
    source: SourceType
