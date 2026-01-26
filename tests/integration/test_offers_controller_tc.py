import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import EmailStr

from app.common.slack.factory import get_slack_notifier

# Helper to build a raw-offer payload compatible with the API
from app.common.slack.SlackNotifierBase import SlackNotifierBase
from app.schemas.api.api_responses import ParseResponse, SubstitutionOffer
from app.service.parsers.factory import get_ai_parser


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
        "lat": lat,
        "lon": lon,
        "lat_min": lat - 0.1,
        "lat_max": lat + 0.1,
        "lon_min": lon - 0.1,
        "lon_max": lon + 0.1,
        "population": 100000,
        "importance": 0.9,
        "category": "city",
        "state": None,
        "voivodeship_name": voivodeship_name,
        "voivodeship_iso": voivodeship_iso,
        "teryt_simc": teryt,
    }


class DummySlackNotifier(SlackNotifierBase):
    async def send_message(self, text: str) -> None:
        return None

    async def send_rich_message(self, text: str) -> None:
        return None

    async def send_new_offer_notification(self, author: str, email: EmailStr, description: str, offer_uuid: str) -> None:
        return None

    async def send_new_offer_rich_notification(self, author: str, email: EmailStr, description: str, offer_uuid: str) -> None:
        return None


class DummyParser:
    async def parse_offer(self, raw_data: str) -> ParseResponse:
        return ParseResponse(
            success=True,
            data=SubstitutionOffer(
                location="policja",
                location_full_name="Police Station",
                description="Parsed offer",
                legal_roles=["adwokat"],
                email="parsed@example.com",
            ),
        )


@pytest.fixture()
def client_with_overrides(client):
    client.app.dependency_overrides[get_slack_notifier] = lambda: DummySlackNotifier()
    client.app.dependency_overrides[get_ai_parser] = lambda: DummyParser()
    try:
        yield client
    finally:
        client.app.dependency_overrides.pop(get_slack_notifier, None)
        client.app.dependency_overrides.pop(get_ai_parser, None)


@pytest.mark.integration
def test_create_and_list_raw_offers(client):
    # create two offers
    r1 = client.post("/offers/raw", json=make_offer_payload("o-1"))
    assert r1.status_code == 201

    r2 = client.post("/offers/raw", json=make_offer_payload("o-2", author="alice", author_uid="u2"))
    assert r2.status_code == 201

    # list
    res = client.get("/offers/raw", params={"limit": 10, "offset": 0, "order": "asc", "field": "created_at"})
    assert res.status_code == 200
    body = res.json()

    assert body["limit"] == 10
    assert body["offset"] == 0
    assert body["count"] >= 2
    assert len(body["data"]) >= 2

    # Ensure important fields exist
    item = body["data"][0]
    assert {"uuid", "author", "author_uid", "offer_uid", "raw_data", "source", "added_at", "email"}.issubset(item.keys())
    offer_uids = {item["offer_uid"] for item in body["data"]}
    assert {"o-1", "o-2"}.issubset(offer_uids)


@pytest.mark.integration
def test_list_offers(client_with_overrides):
    city_name = f"ListCity-{uuid4().hex[:6]}"
    create_city = client_with_overrides.post("/places/city", json=make_city_payload(city_name, teryt=f"SIMC-{uuid4().hex[:6]}"))
    assert create_city.status_code == 200
    city_search = client_with_overrides.get(f"/places/city/{city_name}")
    assert city_search.status_code == 200
    city_uuid = city_search.json()[0]["uuid"]

    roles_resp = client_with_overrides.get("/offers/legal_roles")
    assert roles_resp.status_code == 200
    role_uuid = roles_resp.json()[0]["uuid"]

    description = f"list-offer-{uuid4().hex[:8]}"
    payload = make_offer_create_payload(description, email="list@example.com")
    payload["city_uuid"] = city_uuid
    payload["roles"] = [role_uuid]
    payload["invoice"] = True
    created = client_with_overrides.post("/offers", json=payload)
    assert created.status_code == 201

    listed = client_with_overrides.get(
        "/offers",
        params={
            "search": description,
            "limit": 10,
            "offset": 0,
            "field": "valid_to",
            "order": "asc",
            "legal_role_uuids": [role_uuid],
            "invoice": True,
        },
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body["count"] >= 1
    assert body["data"], "Expected at least one offer in list"
    assert any(item["description"] == description for item in body["data"])


@pytest.mark.integration
def test_duplicate_offer_returns_409(client):
    payload = make_offer_payload("o-dup")

    r1 = client.post("/offers/raw", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/offers/raw", json=payload)
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"]


@pytest.mark.integration
def test_accept_raw_offer_and_status_changes(client):
    # create new offer
    client.post("/offers/raw", json=make_offer_payload("o-acc"))

    # fetch its uuid from raw list
    raw = client.get("/offers/raw")
    uuids = [item["uuid"] for item in raw.json()["data"] if item["offer_uid"] == "o-acc"]
    assert uuids, "Newly created offer should be retrievable"
    offer_uuid = uuids[0]

    # accept the offer
    patch = client.patch(f"/offers/raw/{offer_uuid}/accept")
    assert patch.status_code == 204

    # verify status through raw-offer read endpoint
    got = client.get(f"/offers/raw/{offer_uuid}")
    assert got.status_code == 200
    assert got.json()["status"].lower() == "active"


@pytest.mark.integration
def test_reject_raw_offer_and_status_changes(client):
    # create new offer
    client.post("/offers/raw", json=make_offer_payload("o-rej"))

    # fetch its uuid from raw list
    raw = client.get("/offers/raw")
    uuids = [item["uuid"] for item in raw.json()["data"] if item["offer_uid"] == "o-rej"]
    assert uuids, "Newly created offer should be retrievable"
    offer_uuid = uuids[0]

    # reject the offer
    patch = client.patch(f"/offers/raw/{offer_uuid}/reject")
    assert patch.status_code == 204

    # verify status through raw-offer read endpoint
    got = client.get(f"/offers/raw/{offer_uuid}")
    assert got.status_code == 200
    assert got.json()["status"].lower() == "rejected"


@pytest.mark.integration
def test_list_legal_roles_and_count(client_with_overrides):
    roles = client_with_overrides.get("/offers/legal_roles")
    assert roles.status_code == 200
    roles_body = roles.json()
    assert isinstance(roles_body, list)
    assert roles_body, "Seeded legal roles should be present"

    city_name = f"CountCity-{uuid4().hex[:6]}"
    create_city = client_with_overrides.post("/places/city", json=make_city_payload(city_name, teryt=f"SIMC-{uuid4().hex[:6]}"))
    assert create_city.status_code == 200
    city_search = client_with_overrides.get(f"/places/city/{city_name}")
    assert city_search.status_code == 200
    city_uuid = city_search.json()[0]["uuid"]

    description = f"count-test-{uuid4().hex[:8]}"
    payload = make_offer_create_payload(description, email="count@example.com")
    payload["city_uuid"] = city_uuid
    created = client_with_overrides.post("/offers", json=payload)
    assert created.status_code == 201

    count = client_with_overrides.get("/offers/count")
    assert count.status_code == 200
    assert count.json()["count"] >= 1


@pytest.mark.integration
def test_create_list_get_update_offer_and_email_similar(client_with_overrides):
    description = f"offer-{uuid4().hex[:8]}"
    email = "offer@example.com"
    payload = make_offer_create_payload(description, email=email)

    city_name = f"OfferCity-{uuid4().hex[:6]}"
    create_city = client_with_overrides.post("/places/city", json=make_city_payload(city_name, teryt=f"SIMC-{uuid4().hex[:6]}"))
    assert create_city.status_code == 200
    city_search = client_with_overrides.get(f"/places/city/{city_name}")
    assert city_search.status_code == 200
    payload["city_uuid"] = city_search.json()[0]["uuid"]

    created = client_with_overrides.post("/offers", json=payload)
    assert created.status_code == 201

    listed = client_with_overrides.get("/offers", params={"search": description})
    assert listed.status_code == 200
    listed_body = listed.json()
    assert listed_body["count"] >= 1
    assert listed_body["data"], "Should return at least one offer"
    offer_uuid = listed_body["data"][0]["uuid"]

    got = client_with_overrides.get(f"/offers/{offer_uuid}")
    assert got.status_code == 200
    got_body = got.json()
    assert got_body["uuid"] == offer_uuid

    updated = client_with_overrides.patch(f"/offers/{offer_uuid}", json={"description": "updated desc", "author": "jane"})
    assert updated.status_code == 204

    got_after = client_with_overrides.get(f"/offers/{offer_uuid}")
    assert got_after.status_code == 200
    assert got_after.json()["description"] == "updated desc"

    email_resp = client_with_overrides.get(f"/offers/{offer_uuid}/email")
    assert email_resp.status_code == 200
    assert email_resp.json()["email"] == email

    second_payload = make_offer_create_payload(f"offer-{uuid4().hex[:8]}", email=email)
    second_payload["city_uuid"] = payload["city_uuid"]
    second = client_with_overrides.post("/offers", json=second_payload)
    assert second.status_code == 201

    similar = client_with_overrides.get(f"/offers/{offer_uuid}/similar")
    assert similar.status_code == 200
    similar_body = similar.json()
    assert isinstance(similar_body, list)
    assert any(item["uuid"] == offer_uuid for item in similar_body)


@pytest.mark.integration
def test_list_map_offers(client_with_overrides):
    city_name = f"MapCity-{uuid4().hex[:6]}"
    create_city = client_with_overrides.post("/places/city", json=make_city_payload(city_name, teryt=f"SIMC-{uuid4().hex[:6]}"))
    assert create_city.status_code == 200

    city_search = client_with_overrides.get(f"/places/city/{city_name}")
    assert city_search.status_code == 200
    city_uuid = city_search.json()[0]["uuid"]

    payload = make_offer_create_payload(f"map-offer-{uuid4().hex[:8]}", email="map@example.com")
    payload["city_uuid"] = city_uuid
    created = client_with_overrides.post("/offers", json=payload)
    assert created.status_code == 201

    map_resp = client_with_overrides.get("/offers/map")
    assert map_resp.status_code == 200
    assert isinstance(map_resp.json(), list)


@pytest.mark.integration
def test_import_and_parse_raw_offer(client_with_overrides):
    created = client_with_overrides.post("/offers/raw", json=make_offer_payload(f"o-parse-{uuid4().hex[:6]}"))
    assert created.status_code == 201

    raw_list = client_with_overrides.get("/offers/raw", params={"limit": 50, "offset": 0})
    assert raw_list.status_code == 200
    raw_items = raw_list.json()["data"]
    offer_uuids = [item["uuid"] for item in raw_items if item["offer_uid"].startswith("o-parse-")]
    assert offer_uuids, "Raw offer should be present for parsing"
    offer_uuid = offer_uuids[0]

    raw_offer = client_with_overrides.get(f"/offers/raw/{offer_uuid}")
    assert raw_offer.status_code == 200

    parsed = client_with_overrides.get(f"/offers/raw/{offer_uuid}/parse")
    assert parsed.status_code == 200
    parsed_body = parsed.json()
    assert parsed_body["success"] is True

    post_url = f"https://fb.test/{uuid4().hex}"
    import_payload = [
        {
            "User Name": "Importer",
            "User Profile URL": "https://fb.test/user",
            "Post URL": post_url,
            "Post Content": "Need substitution mail@test.local",
            "Date Posted": "2024-01-01T10:00:00",
        }
    ]
    files = {"file": ("offers.json", json.dumps(import_payload).encode("utf-8"), "application/json")}

    imported = client_with_overrides.post("/offers/raw/import", files=files)
    assert imported.status_code == 200
    imported_body = imported.json()
    assert imported_body["total_records"] == 1
    assert imported_body["imported_records"] == 1
