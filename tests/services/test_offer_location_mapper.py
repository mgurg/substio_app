from unittest.mock import MagicMock

from app.database.models.models import Offer
from app.services.offers.offer_location_mapper import OfferLocationMapper


class MockEntity:
    def __init__(self, id, lat, lon, name):
        self.id = id
        self.lat = lat
        self.lon = lon
        self.name = name


def test_assign_place_to_data():
    # Given
    offer_data = {}
    place = MockEntity(id=1, lat=52.2297, lon=21.0122, name="Place 1")

    # When
    OfferLocationMapper.assign_place_to_data(offer_data, place)

    # Then
    assert offer_data["place_id"] == 1
    assert offer_data["lat"] == 52.2297
    assert offer_data["lon"] == 21.0122


def test_assign_city_to_data():
    # Given
    offer_data = {}
    city = MockEntity(id=2, lat=50.0647, lon=19.9450, name="City 2")

    # When
    OfferLocationMapper.assign_city_to_data(offer_data, city)

    # Then
    assert offer_data["city_id"] == 2
    assert offer_data["lat"] == 50.0647
    assert offer_data["lon"] == 19.9450


def test_assign_place_to_offer():
    # Given
    db_offer = MagicMock(spec=Offer)
    place = MockEntity(id=1, lat=52.2297, lon=21.0122, name="Place 1")

    # When
    OfferLocationMapper.assign_place_to_offer(db_offer, place)

    # Then
    assert db_offer.lat == 52.2297
    assert db_offer.lon == 21.0122
    assert db_offer.place == place


def test_assign_city_to_offer():
    # Given
    db_offer = MagicMock(spec=Offer)
    city = MockEntity(id=2, lat=50.0647, lon=19.9450, name="City 2")

    # When
    OfferLocationMapper.assign_city_to_offer(db_offer, city)

    # Then
    assert db_offer.lat == 50.0647
    assert db_offer.lon == 19.9450
    assert db_offer.city == city


def test_assign_place_to_data_none():
    # Given
    offer_data = {}

    # When
    OfferLocationMapper.assign_place_to_data(offer_data, None)

    # Then
    assert "place_id" not in offer_data
    assert "lat" not in offer_data
    assert "lon" not in offer_data


def test_assign_city_to_data_none():
    # Given
    offer_data = {}

    # When
    OfferLocationMapper.assign_city_to_data(offer_data, None)

    # Then
    assert "city_id" not in offer_data
    assert "lat" not in offer_data
    assert "lon" not in offer_data


def test_assign_place_to_offer_none():
    # Given
    db_offer = MagicMock(spec=Offer)
    db_offer.lat = 1.0

    # When
    OfferLocationMapper.assign_place_to_offer(db_offer, None)

    # Then
    # Should not change anything
    assert db_offer.lat == 1.0


def test_assign_city_to_offer_none():
    # Given
    db_offer = MagicMock(spec=Offer)
    db_offer.lat = 1.0

    # When
    OfferLocationMapper.assign_city_to_offer(db_offer, None)

    # Then
    # Should not change anything
    assert db_offer.lat == 1.0
