from decimal import Decimal
from uuid import UUID

from app.database.models.enums import PlaceCategory
from app.schemas.domain.place import CityAdd, PlaceAdd
from app.services.places.city_mapper import CityMapper
from app.services.places.place_mapper import PlaceMapper


def test_place_mapper_to_db_dict():
    place_add = PlaceAdd(
        category=PlaceCategory.COURT,
        name="Test Court",
        lat=Decimal("52.2297"),
        lon=Decimal("21.0122"),
        city="Warszawa",
        street="Al. Solidarności 127"
    )

    result = PlaceMapper.map_to_db_dict(place_add)

    assert "uuid" in result
    assert isinstance(UUID(result["uuid"]), UUID)
    assert result["name"] == "Test Court"
    assert result["city"] == "Warszawa"
    assert result["street_name"] == "Al. Solidarności"
    assert result["street_number"] == "127"
    assert result["lat"] == Decimal("52.2297")
    assert result["lon"] == Decimal("21.0122")
    assert result["name_ascii"] == "test-court"


def test_city_mapper_to_db_dict():
    city_add = CityAdd(
        city_name="Warszawa",
        lat=Decimal("52.2297"),
        lon=Decimal("21.0122"),
        category="city",
        voivodeship_name="Mazowieckie",
        voivodeship_iso="MZ",
        teryt_simc="1234567"
    )

    result = CityMapper.map_to_db_dict(city_add)

    assert "uuid" in result
    assert isinstance(UUID(result["uuid"]), UUID)
    assert result["name"] == "Warszawa"
    assert result["name_ascii"] == "warszawa"
    assert result["lat"] == Decimal("52.2297")
    assert result["lon"] == Decimal("21.0122")
    assert result["teryt_simc"] == "1234567"
