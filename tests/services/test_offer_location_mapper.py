import pytest
from unittest.mock import MagicMock
from app.database.models.models import Offer
from app.services.offers.offer_location_mapper import OfferLocationMapper

class MockEntity:
    def __init__(self, id, lat, lon):
        self.id = id
        self.lat = lat
        self.lon = lon

def test_assign_place_to_data():
    offer_data = {}
    place = MockEntity(id=1, lat=52.2297, lon=21.0122)
    OfferLocationMapper.assign_place_to_data(offer_data, place)
    
    assert offer_data["place_id"] == 1
    assert offer_data["lat"] == 52.2297
    assert offer_data["lon"] == 21.0122

def test_assign_city_to_data():
    offer_data = {}
    city = MockEntity(id=2, lat=50.0647, lon=19.9450)
    OfferLocationMapper.assign_city_to_data(offer_data, city)
    
    assert offer_data["city_id"] == 2
    assert offer_data["lat"] == 50.0647
    assert offer_data["lon"] == 19.9450

def test_assign_place_to_offer():
    db_offer = MagicMock(spec=Offer)
    place = MockEntity(id=1, lat=52.2297, lon=21.0122)
    OfferLocationMapper.assign_place_to_offer(db_offer, place)
    
    assert db_offer.lat == 52.2297
    assert db_offer.lon == 21.0122
    assert db_offer.place == place

def test_assign_city_to_offer():
    db_offer = MagicMock(spec=Offer)
    city = MockEntity(id=2, lat=50.0647, lon=19.9450)
    OfferLocationMapper.assign_city_to_offer(db_offer, city)
    
    assert db_offer.lat == 50.0647
    assert db_offer.lon == 19.9450
    assert db_offer.city == city
