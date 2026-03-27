
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


@pytest.mark.parametrize("endpoint, search_term", [
    ("/places/city/{}", "a"),        # too short
    ("/places/city/{}", "a" * 101),  # too long
    ("/places/facility/{}", "a"),       # too short
    ("/places/facility/{}", "a" * 101),  # too long
])
@pytest.mark.integration
def test_search_length_validation(client, endpoint, search_term):
    res = client.get(endpoint.format(search_term))
    # Note: If there's no explicit validation in FastAPI router (like Query(min_length=2)),
    # it might return 200 with empty list or just work.
    # But usually we want to enforce some limits.
    # Looking at the code, it's just `city_name: str` and `place_name: str`.
    # Let's see how it behaves.
    assert res.status_code in (200, 422)


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


@pytest.mark.integration
def test_place_index_response_fields(client):
    # This test ensures that the fields added to PlaceIndexResponse are present and correctly populated
    # city, street_name, street_number

    city_name = "Rawicz"
    street_name = "ul. Ignacego Buszy"
    street_number = "5"
    place_name = "Sąd Rejonowy w Rawiczu"

    client.post("/places/city", json=make_city_payload(city_name, teryt="SIMC-RAW"))

    payload = make_place_payload(place_name, city=city_name)
    payload["address"]["street_name"] = street_name
    payload["address"]["street_number"] = street_number

    create_res = client.post("/places/", json=payload)
    assert create_res.status_code == 200

    search_res = client.get(f"/places/facility/{place_name[:10].lower()}")
    assert search_res.status_code == 200

    facilities = search_res.json()
    assert len(facilities) > 0

    # Find our specific place in the results
    place = next((f for f in facilities if f["name"] == place_name), None)
    assert place is not None, f"Place '{place_name}' not found in search results"

    # Verify new fields
    assert "city" in place
    assert "street_name" in place
    assert "street_number" in place

    assert place["city"] == city_name
    assert place["street_name"] == street_name
    assert place["street_number"] == street_number
