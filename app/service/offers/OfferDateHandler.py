from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST


class OfferDateHandler:
    @staticmethod
    def parse_date(date_str: str) -> date:
        """Parse date string with error handling"""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid date format") from e

    @staticmethod
    def parse_hour(hour_str: str) -> time:
        """Parse hour string with error handling"""
        try:
            return datetime.strptime(hour_str, "%H:%M").time()
        except ValueError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid hour format") from e

    @staticmethod
    def compute_valid_to(date_obj: date | None, hour_obj: time | None) -> datetime:
        """Compute valid_to timestamp based on date and hour"""
        if date_obj and hour_obj:
            combined = datetime.combine(date_obj, hour_obj)
            warsaw_tz = ZoneInfo("Europe/Warsaw")
            return combined.replace(tzinfo=warsaw_tz).astimezone(ZoneInfo("UTC"))

        return datetime.now(UTC) + timedelta(days=7)

    @classmethod
    def parse_date_hour(cls, date_str: str | None, hour_str: str | None) -> tuple[date | None, time | None]:
        date_obj = cls.parse_date(date_str) if date_str else None
        hour_obj = cls.parse_hour(hour_str) if hour_str else None
        return date_obj, hour_obj
