
import pytest

from tests.utils.test_helpers import make_city_payload, make_place_payload


@pytest.mark.integration
def test_create_and_search_cities(client):
    # create two cities
    r1 = client.post("/places/city", json=make_city_payload("Warszawa", teryt="SIMC-1"))
    assert r1.status_code == 200

    r2 = client.post("/places/city", json=make_city_payload("Warka", teryt="SIMC-2", lat=51.78, lon=21.19))
    assert r2.status_code == 200

    # search by partial name
    res = client.get("/places/city/war")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(item["name"].lower().startswith("war") for item in data)

    # Ensure important fields exist
    item = data[0]
    assert {"uuid", "name", "lat", "lon", "voivodeship_name"}.issubset(item.keys())


@pytest.mark.integration
def test_duplicate_city_returns_409(client):
    payload = make_city_payload("Radom", teryt="SIMC-DUP")

    r1 = client.post("/places/city", json=payload)
    assert r1.status_code == 200

    r2 = client.post("/places/city", json=payload)
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"].lower()


@pytest.mark.integration
def test_create_place_and_get_by_uuid(client):
    # Ensure city exists (optional for the endpoint but realistic)
    client.post("/places/city", json=make_city_payload("Alpha City", teryt="SIMC-A1"))

    # create a place
    pr = client.post("/places/", json=make_place_payload("Test Place Alpha", city="Alpha City"))
    assert pr.status_code == 200

    # search facilities by partial name
    res = client.get("/places/facility/test place")
    assert res.status_code == 200
    facilities = res.json()
    assert isinstance(facilities, list)
    assert any("test place" in f["name"].lower() for f in facilities)

    # pick one and fetch by uuid
    place_uuid = facilities[0]["uuid"]
    got = client.get(f"/places/facility/uuid/{place_uuid}")
    assert got.status_code == 200
    body = got.json()
    assert body["uuid"] == place_uuid
    assert body["name"]
    assert body["category"] in {"court", "police", "prosecutor", "other"}


@pytest.mark.integration
def test_duplicate_place_returns_409(client):
    payload = make_place_payload("Duplicate Court", lat=52.23, lon=21.01)

    r1 = client.post("/places/", json=payload)
    assert r1.status_code == 200

    r2 = client.post("/places/", json=payload)
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"].lower()


@pytest.mark.integration
def test_get_city_by_uuid(client):
    # create city
    client.post("/places/city", json=make_city_payload("Gamma", teryt="SIMC-G1"))

    # find via search
    res = client.get("/places/city/gam")
    assert res.status_code == 200
    cities = res.json()
    assert cities, "City search should return at least one item"
    city_uuid = cities[0]["uuid"]

    # get by uuid
    got = client.get(f"/places/city/uuid/{city_uuid}")
    assert got.status_code == 200
    body = got.json()
    assert body["uuid"] == city_uuid
    assert body["name"] == cities[0]["name"]
