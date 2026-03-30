from datetime import UTC, datetime
from uuid import uuid4

# --- Places Payloads ---


def make_city_payload(
    name: str,
    *,
    teryt: str,
    voivodeship_name: str = "Mazowieckie",
    voivodeship_iso: str = "MZ",
    lat: float = 52.2297,
    lon: float = 21.0122,
) -> dict:
    return {
        "city_name": name,
        "coordinates": {"lat": lat, "lon": lon},
        "range": {
            "lat_min": lat - 0.1,
            "lat_max": lat + 0.1,
            "lon_min": lon - 0.1,
            "lon_max": lon + 0.1,
        },
        "population": 100000,
        "importance": 0.9,
        "category": "city",
        "state": None,
        "voivodeship_name": voivodeship_name,
        "voivodeship_iso": voivodeship_iso,
        "teryt_simc": teryt,
    }


def make_place_payload(
    name: str,
    *,
    category: str = "court",
    ptype: str = "SR",
    street: str = "Main 12",
    city: str = "Warszawa",
    lat: float = 52.2297,
    lon: float = 21.0122,
) -> dict:
    return {
        "category": category,
        "type": ptype,
        "name": name,
        "address": {
            "street": street,
            "street_name": None,
            "street_number": None,
            "postal_code": "00-001",
            "city": city,
        },
        "phone": None,
        "email": None,
        "department": None,
        "coordinates": {"lat": lat, "lon": lon},
        "website": None,
    }


# --- Offers Payloads ---

def make_offer_payload(uid: str, author: str = "john", author_uid: str = "u1") -> dict:
    return {
        "raw_data": "Some raw offer text about case in court with mail@mail.com",
        "author": author,
        "author_uid": author_uid,
        "offer_uid": uid,
        "timestamp": datetime.now(UTC).isoformat(),
        "source": "bot",
    }


def make_offer_create_payload(description: str, email: str, author: str = "john") -> dict:
    return {
        "author": author,
        "email": email,
        "description": description,
        "source": "user",
    }


# --- Setup Helpers ---

def setup_test_city(client, name_prefix="TestCity") -> str:
    """Helper to create a test city and return its UUID"""
    from app.common.text_utils import sanitize_name

    city_name = f"{name_prefix}-{uuid4().hex[:6]}"
    res = client.post("/places/city", json=make_city_payload(city_name, teryt=f"SIMC-{uuid4().hex[:6]}"))
    assert res.status_code == 200, f"Failed to create city: {res.text}"

    # Search by sanitized name since GET /city/{city_name} uses it
    sanitized = sanitize_name(city_name)
    response = client.get(f"/places/city/{sanitized}")
    assert response.status_code == 200, f"Failed to get city: {response.text}"
    data = response.json()
    assert len(data) > 0, f"City not found: {city_name} (sanitized: {sanitized})"
    return data[0]["uuid"]


def create_test_offer(client, description=None, **kwargs) -> str:
    """Helper to create a test offer and return its UUID"""
    if description is None:
        description = f"test-{uuid4().hex[:8]}"

    payload = make_offer_create_payload(description, f"{description}@test.com")
    payload.update(kwargs)

    if "city_uuid" not in payload:
        payload["city_uuid"] = setup_test_city(client)

    client.post("/offers", json=payload)
    response = client.get("/offers", params={"search": description})
    return response.json()["data"][0]["uuid"]
