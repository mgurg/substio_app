from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.domain.common import CoordinateRange, Coordinates
from app.schemas.validators.validators import round_to_7_decimal_places


def test_round_to_7_decimal_places_direct():
    # Test with float
    assert round_to_7_decimal_places(52.123456789) == Decimal("52.1234567")

    # Test with string
    assert round_to_7_decimal_places("21.987654321") == Decimal("21.9876543")

    # Test with Decimal
    assert round_to_7_decimal_places(Decimal("10.111111111")) == Decimal("10.1111111")

    # Test with None
    assert round_to_7_decimal_places(None) is None

    # Test with invalid value
    with pytest.raises(ValueError, match="Invalid coordinate format"):
        round_to_7_decimal_places("not-a-number")


def test_coordinates_schema_validation():
    # Test that Coordinates schema correctly uses the validator
    coords = Coordinates(lat=52.123456789, lon="21.987654321")
    assert coords.lat == Decimal("52.1234567")
    assert coords.lon == Decimal("21.9876543")


def test_coordinate_range_schema_validation():
    # Test that CoordinateRange schema correctly uses the validator
    c_range = CoordinateRange(
        lat_min=52.123456789,
        lat_max="52.222222222",
        lon_min=Decimal("21.111111111"),
        lon_max=21.999999999
    )
    assert c_range.lat_min == Decimal("52.1234567")
    assert c_range.lat_max == Decimal("52.2222222")
    assert c_range.lon_min == Decimal("21.1111111")
    assert c_range.lon_max == Decimal("21.9999999")


def test_coordinates_validation_error():
    # Test that invalid values still raise errors via Pydantic/Validator
    with pytest.raises(ValidationError):
        Coordinates(lat="invalid", lon=21.0)

    # Test out of range (Pydantic Field constraints)
    with pytest.raises(ValidationError):
        Coordinates(lat=100.0, lon=21.0)
