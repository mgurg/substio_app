import pytest
from datetime import date, time, datetime, UTC, timedelta
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from app.services.offers.offer_date_handler import OfferDateHandler

def test_parse_date_success():
    assert OfferDateHandler.parse_date("2024-03-14") == date(2024, 3, 14)

def test_parse_date_invalid_format():
    with pytest.raises(HTTPException) as excinfo:
        OfferDateHandler.parse_date("14-03-2024")
    assert excinfo.value.status_code == 400
    assert "Invalid date format" in excinfo.value.detail

def test_parse_hour_success():
    assert OfferDateHandler.parse_hour("15:30") == time(15, 30)

def test_parse_hour_invalid_format():
    with pytest.raises(HTTPException) as excinfo:
        OfferDateHandler.parse_hour("3:30 PM")
    assert excinfo.value.status_code == 400
    assert "Invalid hour format" in excinfo.value.detail

def test_compute_valid_to_with_date_and_hour():
    date_obj = date(2024, 3, 14)
    hour_obj = time(15, 30)
    
    # Warsaw is UTC+1 in March 14th (before DST change which is usually last Sunday of March)
    # 15:30 Warsaw should be 14:30 UTC
    expected_utc = datetime(2024, 3, 14, 14, 30, tzinfo=UTC)
    
    result = OfferDateHandler.compute_valid_to(date_obj, hour_obj)
    assert result == expected_utc

def test_compute_valid_to_with_date_and_hour_dst():
    # July is DST in Warsaw (UTC+2)
    date_obj = date(2024, 7, 14)
    hour_obj = time(15, 30)
    
    # 15:30 Warsaw should be 13:30 UTC
    expected_utc = datetime(2024, 7, 14, 13, 30, tzinfo=UTC)
    
    result = OfferDateHandler.compute_valid_to(date_obj, hour_obj)
    assert result == expected_utc

def test_compute_valid_to_none_returns_default():
    result = OfferDateHandler.compute_valid_to(None, None)
    # Default is approx now + 7 days
    now = datetime.now(UTC)
    expected_min = now + timedelta(days=6, hours=23)
    expected_max = now + timedelta(days=7, hours=1)
    
    assert expected_min < result < expected_max
    assert result.tzinfo == UTC

def test_parse_date_hour_both():
    d, h = OfferDateHandler.parse_date_hour("2024-03-14", "15:30")
    assert d == date(2024, 3, 14)
    assert h == time(15, 30)

def test_parse_date_hour_none():
    d, h = OfferDateHandler.parse_date_hour(None, None)
    assert d is None
    assert h is None
