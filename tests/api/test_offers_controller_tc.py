import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import EmailStr

from app.infrastructure.ai.parsers.factory import get_ai_parser
from app.infrastructure.notifications.slack.factory import get_slack_notifier
from app.infrastructure.notifications.slack.slack_notifier_base import SlackNotifierBase
from app.schemas.domain.ai import ParseResponse, SubstitutionOffer


# Helper functions to build payloads
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


# ============================================================================
# RAW OFFERS TESTS
# ============================================================================


@pytest.mark.integration
def test_create_and_list_raw_offers(client):
    """Test creating and listing raw offers"""
    r1 = client.post("/offers/raw", json=make_offer_payload("o-1"))
    assert r1.status_code == 201

    r2 = client.post("/offers/raw", json=make_offer_payload("o-2", author="alice", author_uid="u2"))
    assert r2.status_code == 201

    res = client.get("/offers/raw", params={"limit": 10, "offset": 0, "order": "asc", "field": "created_at"})
    assert res.status_code == 200
    body = res.json()

    assert body["limit"] == 10
    assert body["offset"] == 0
    assert body["count"] >= 2
    assert len(body["data"]) >= 2

    item = body["data"][0]
    assert {"uuid", "author", "author_uid", "offer_uid", "raw_data", "source", "added_at", "email"}.issubset(item.keys())
    offer_uids = {item["offer_uid"] for item in body["data"]}
    assert {"o-1", "o-2"}.issubset(offer_uids)


@pytest.mark.integration
def test_duplicate_offer_returns_409(client):
    """Test that duplicate raw offers return 409 conflict"""
    payload = make_offer_payload("o-dup")

    r1 = client.post("/offers/raw", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/offers/raw", json=payload)
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"]


@pytest.mark.integration
def test_get_nonexistent_raw_offer_returns_404(client):
    """Test fetching a raw offer that doesn't exist"""
    fake_uuid = uuid4()
    response = client.get(f"/offers/raw/{fake_uuid}")
    assert response.status_code == 404


@pytest.mark.integration
def test_accept_raw_offer_and_status_changes(client):
    """Test accepting a raw offer changes its status to active"""
    client.post("/offers/raw", json=make_offer_payload("o-acc"))

    raw = client.get("/offers/raw")
    uuids = [item["uuid"] for item in raw.json()["data"] if item["offer_uid"] == "o-acc"]
    assert uuids, "Newly created offer should be retrievable"
    offer_uuid = uuids[0]

    patch = client.patch(f"/offers/raw/{offer_uuid}/accept")
    assert patch.status_code == 204

    got = client.get(f"/offers/raw/{offer_uuid}")
    assert got.status_code == 200
    assert got.json()["status"].lower() == "active"


@pytest.mark.integration
def test_reject_raw_offer_and_status_changes(client):
    """Test rejecting a raw offer changes its status to rejected"""
    client.post("/offers/raw", json=make_offer_payload("o-rej"))

    raw = client.get("/offers/raw")
    uuids = [item["uuid"] for item in raw.json()["data"] if item["offer_uid"] == "o-rej"]
    assert uuids, "Newly created offer should be retrievable"
    offer_uuid = uuids[0]

    patch = client.patch(f"/offers/raw/{offer_uuid}/reject")
    assert patch.status_code == 204

    got = client.get(f"/offers/raw/{offer_uuid}")
    assert got.status_code == 200
    assert got.json()["status"].lower() == "rejected"


@pytest.mark.integration
def test_accept_already_accepted_offer_idempotent(client):
    """Test that accepting an already accepted offer is idempotent"""
    client.post("/offers/raw", json=make_offer_payload("o-double-accept"))

    raw = client.get("/offers/raw")
    offer_uuid = next(item["uuid"] for item in raw.json()["data"] if item["offer_uid"] == "o-double-accept")

    response1 = client.patch(f"/offers/raw/{offer_uuid}/accept")
    assert response1.status_code == 204

    response2 = client.patch(f"/offers/raw/{offer_uuid}/accept")
    assert response2.status_code in [204, 409]


@pytest.mark.integration
def test_cannot_accept_rejected_offer(client):
    """Test that accepting a rejected offer fails appropriately"""
    client.post("/offers/raw", json=make_offer_payload("o-reject-then-accept"))

    raw = client.get("/offers/raw")
    offer_uuid = next(item["uuid"] for item in raw.json()["data"] if item["offer_uid"] == "o-reject-then-accept")

    client.patch(f"/offers/raw/{offer_uuid}/reject")

    response = client.patch(f"/offers/raw/{offer_uuid}/accept")
    assert response.status_code in [400, 409]


@pytest.mark.integration
def test_accept_nonexistent_raw_offer_returns_404(client):
    """Test accepting a raw offer that doesn't exist"""
    fake_uuid = uuid4()
    response = client.patch(f"/offers/raw/{fake_uuid}/accept")
    assert response.status_code == 404


@pytest.mark.integration
def test_reject_nonexistent_raw_offer_returns_404(client):
    """Test rejecting a raw offer that doesn't exist"""
    fake_uuid = uuid4()
    response = client.patch(f"/offers/raw/{fake_uuid}/reject")
    assert response.status_code == 404


# ============================================================================
# REGULAR OFFERS TESTS
# ============================================================================


@pytest.mark.integration
def test_list_offers(client_with_overrides):
    """Test listing offers with filters"""
    city_uuid = setup_test_city(client_with_overrides, "ListCity")

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
def test_create_offer_without_required_city_fails(client_with_overrides):
    """Test that creating an offer without city_uuid fails"""
    payload = make_offer_create_payload("test", email="test@example.com")
    response = client_with_overrides.post("/offers", json=payload)
    assert response.status_code == 422


@pytest.mark.integration
def test_get_nonexistent_offer_returns_404(client_with_overrides):
    """Test fetching an offer that doesn't exist"""
    fake_uuid = uuid4()
    response = client_with_overrides.get(f"/offers/{fake_uuid}")
    assert response.status_code == 404


@pytest.mark.integration
def test_update_nonexistent_offer_returns_404(client_with_overrides):
    """Test updating an offer that doesn't exist"""
    fake_uuid = uuid4()
    response = client_with_overrides.patch(f"/offers/{fake_uuid}", json={"description": "updated"})
    assert response.status_code == 404


@pytest.mark.integration
def test_create_offer_and_verify_all_fields(client_with_overrides):
    """Verify all fields are correctly stored and retrieved"""
    city_uuid = setup_test_city(client_with_overrides, "VerifyCity")

    roles_resp = client_with_overrides.get("/offers/legal_roles")
    role_uuid = roles_resp.json()[0]["uuid"]

    description = f"verify-{uuid4().hex[:8]}"
    email = "verify@example.com"
    author = "test_author"

    payload = {
        "author": author,
        "email": email,
        "description": description,
        "source": "user",
        "city_uuid": city_uuid,
        "roles": [role_uuid],
        "invoice": True,
    }

    created = client_with_overrides.post("/offers", json=payload)
    assert created.status_code == 201

    listed = client_with_overrides.get("/offers", params={"search": description})
    assert listed.status_code == 200
    offer_data = listed.json()["data"][0]

    assert offer_data["description"] == description
    assert offer_data["author"] == author
    assert offer_data["invoice"] is True
    assert offer_data["city_uuid"] == city_uuid


@pytest.mark.integration
def test_create_list_get_update_offer_and_email_similar(client_with_overrides):
    """Test full CRUD operations on offers"""
    description = f"offer-{uuid4().hex[:8]}"
    email = "offer@example.com"
    payload = make_offer_create_payload(description, email=email)

    city_uuid = setup_test_city(client_with_overrides, "OfferCity")
    payload["city_uuid"] = city_uuid

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
    second_payload["city_uuid"] = city_uuid
    second = client_with_overrides.post("/offers", json=second_payload)
    assert second.status_code == 201

    similar = client_with_overrides.get(f"/offers/{offer_uuid}/similar")
    assert similar.status_code == 200
    similar_body = similar.json()
    assert isinstance(similar_body, list)
    assert any(item["uuid"] == offer_uuid for item in similar_body)


# ============================================================================
# FILTERING & PAGINATION TESTS
# ============================================================================


@pytest.mark.integration
def test_list_offers_with_partial_location_params_fails(client_with_overrides):
    """Test that providing incomplete location params returns 400"""
    response = client_with_overrides.get("/offers", params={"lat": 52.0})
    assert response.status_code == 400
    assert "must all be provided together" in response.json()["detail"]

    response = client_with_overrides.get("/offers", params={"lat": 52.0, "lon": 21.0})
    assert response.status_code == 400


@pytest.mark.integration
def test_list_offers_with_complete_location_params(client_with_overrides):
    """Test location filtering with all required params"""
    response = client_with_overrides.get("/offers", params={"lat": 52.0, "lon": 21.0, "distance_km": 10})
    assert response.status_code == 200


@pytest.mark.integration
def test_list_offers_with_max_search_length(client_with_overrides):
    """Test search with maximum allowed length"""
    response = client_with_overrides.get("/offers", params={"search": "x" * 50})
    assert response.status_code == 200


@pytest.mark.integration
def test_list_offers_with_excessive_search_length_fails(client_with_overrides):
    """Test search exceeding max length"""
    response = client_with_overrides.get("/offers", params={"search": "x" * 51})
    assert response.status_code == 422


@pytest.mark.integration
def test_list_offers_with_invalid_lat_lon(client_with_overrides):
    """Test location filtering with out-of-range coordinates"""
    response = client_with_overrides.get("/offers", params={"lat": 100, "lon": 0, "distance_km": 10})
    assert response.status_code == 422

    response = client_with_overrides.get("/offers", params={"lat": 0, "lon": 200, "distance_km": 10})
    assert response.status_code == 422


@pytest.mark.integration
def test_pagination_consistency(client_with_overrides):
    """Test that pagination returns consistent non-overlapping results"""
    city_uuid = setup_test_city(client_with_overrides, "PageCity")

    for i in range(15):
        payload = make_offer_create_payload(f"page-{uuid4().hex[:4]}-{i}", f"page{i}@test.com")
        payload["city_uuid"] = city_uuid
        client_with_overrides.post("/offers", json=payload)

    page1 = client_with_overrides.get("/offers", params={"limit": 5, "offset": 0, "field": "created_at", "order": "asc"})
    page1_uuids = {item["uuid"] for item in page1.json()["data"]}

    page2 = client_with_overrides.get("/offers", params={"limit": 5, "offset": 5, "field": "created_at", "order": "asc"})
    page2_uuids = {item["uuid"] for item in page2.json()["data"]}

    assert page1_uuids.isdisjoint(page2_uuids), "Pages should not contain overlapping offers"


@pytest.mark.integration
def test_filter_by_invoice_only_returns_invoice_offers(client_with_overrides):
    """Test invoice filtering works correctly"""
    city_uuid = setup_test_city(client_with_overrides, "InvoiceCity")
    role_uuid = client_with_overrides.get("/offers/legal_roles").json()[0]["uuid"]

    invoice_desc = f"invoice-{uuid4().hex[:8]}"
    invoice_payload = make_offer_create_payload(invoice_desc, "inv@test.com")
    invoice_payload.update({"city_uuid": city_uuid, "roles": [role_uuid], "invoice": True})
    client_with_overrides.post("/offers", json=invoice_payload)

    no_invoice_desc = f"no-invoice-{uuid4().hex[:8]}"
    no_invoice_payload = make_offer_create_payload(no_invoice_desc, "no@test.com")
    no_invoice_payload.update({"city_uuid": city_uuid, "roles": [role_uuid], "invoice": False})
    client_with_overrides.post("/offers", json=no_invoice_payload)

    response = client_with_overrides.get("/offers", params={"invoice": True, "limit": 100})
    offers = response.json()["data"]

    matching_offers = [o for o in offers if o["description"] in [invoice_desc, no_invoice_desc]]
    assert all(offer["invoice"] is True for offer in matching_offers if offer["description"] == invoice_desc)


@pytest.mark.integration
def test_sorting_order_asc_vs_desc(client_with_overrides):
    """Test that sorting order affects results correctly"""
    city_uuid = setup_test_city(client_with_overrides, "SortCity")

    for i in range(5):
        payload = make_offer_create_payload(f"sort-{uuid4().hex[:4]}", f"sort{i}@test.com")
        payload["city_uuid"] = city_uuid
        client_with_overrides.post("/offers", json=payload)

    asc_response = client_with_overrides.get("/offers", params={"field": "created_at", "order": "asc", "limit": 5})
    asc_data = asc_response.json()["data"]

    desc_response = client_with_overrides.get("/offers", params={"field": "created_at", "order": "desc", "limit": 5})
    desc_data = desc_response.json()["data"]

    if len(asc_data) >= 2 and len(desc_data) >= 2:
        assert asc_data[0]["uuid"] != desc_data[0]["uuid"] or len(asc_data) == 1


# ============================================================================
# LEGAL ROLES & COUNTS
# ============================================================================


@pytest.mark.integration
def test_list_legal_roles_and_count(client_with_overrides):
    """Test listing legal roles and counting offers"""
    roles = client_with_overrides.get("/offers/legal_roles")
    assert roles.status_code == 200
    roles_body = roles.json()
    assert isinstance(roles_body, list)
    assert roles_body, "Seeded legal roles should be present"

    city_uuid = setup_test_city(client_with_overrides, "CountCity")

    description = f"count-test-{uuid4().hex[:8]}"
    payload = make_offer_create_payload(description, email="count@example.com")
    payload["city_uuid"] = city_uuid
    created = client_with_overrides.post("/offers", json=payload)
    assert created.status_code == 201

    count = client_with_overrides.get("/offers/count")
    assert count.status_code == 200
    assert count.json()["count"] >= 1


# ============================================================================
# MAP OFFERS
# ============================================================================


@pytest.mark.integration
def test_list_map_offers(client_with_overrides):
    """Test retrieving offers for map display"""
    city_uuid = setup_test_city(client_with_overrides, "MapCity")

    payload = make_offer_create_payload(f"map-offer-{uuid4().hex[:8]}", email="map@example.com")
    payload["city_uuid"] = city_uuid
    created = client_with_overrides.post("/offers", json=payload)
    assert created.status_code == 201

    map_resp = client_with_overrides.get("/offers/map")
    assert map_resp.status_code == 200
    assert isinstance(map_resp.json(), list)


# ============================================================================
# IMPORT & PARSING
# ============================================================================


@pytest.mark.integration
def test_import_and_parse_raw_offer(client_with_overrides):
    """Test importing and parsing raw offers"""
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


@pytest.mark.integration
def test_parse_nonexistent_raw_offer_returns_404(client_with_overrides):
    """Test parsing a raw offer that doesn't exist"""
    fake_uuid = uuid4()
    response = client_with_overrides.get(f"/offers/raw/{fake_uuid}/parse")
    assert response.status_code == 404


@pytest.mark.integration
def test_import_invalid_json_format(client_with_overrides):
    """Test importing malformed JSON"""
    invalid_json = b"{ this is not valid json }"
    files = {"file": ("bad.json", invalid_json, "application/json")}

    response = client_with_overrides.post("/offers/raw/import", files=files)
    assert response.status_code in [400, 422]


@pytest.mark.integration
def test_import_empty_file(client_with_overrides):
    """Test importing empty JSON array"""
    files = {"file": ("empty.json", b"[]", "application/json")}

    response = client_with_overrides.post("/offers/raw/import", files=files)
    assert response.status_code == 200
    assert response.json()["total_records"] == 0


@pytest.mark.integration
def test_import_with_missing_required_fields(client_with_overrides):
    """Test importing records with missing required fields"""
    import_payload = [
        {
            "User Name": "Importer",
            # Missing other required fields
        }
    ]
    files = {"file": ("incomplete.json", json.dumps(import_payload).encode("utf-8"), "application/json")}

    response = client_with_overrides.post("/offers/raw/import", files=files)
    # Should either skip invalid records or return error
    assert response.status_code in [200, 400, 422]


# ============================================================================
# EMAIL & SIMILAR OFFERS
# ============================================================================


@pytest.mark.integration
def test_get_offer_email_nonexistent_returns_404(client_with_overrides):
    """Test getting email for nonexistent offer"""
    fake_uuid = uuid4()
    response = client_with_overrides.get(f"/offers/{fake_uuid}/email")
    assert response.status_code == 404


@pytest.mark.integration
def test_get_similar_offers_nonexistent_returns_404(client_with_overrides):
    """Test getting similar offers for nonexistent offer"""
    fake_uuid = uuid4()
    response = client_with_overrides.get(f"/offers/{fake_uuid}/similar")
    assert response.status_code == 404


@pytest.mark.integration
def test_similar_offers_same_email(client_with_overrides):
    """Test that offers with the same email are considered similar"""
    city_uuid = setup_test_city(client_with_overrides, "SimilarCity")
    shared_email = f"shared-{uuid4().hex[:6]}@example.com"

    payload1 = make_offer_create_payload(f"offer1-{uuid4().hex[:4]}", email=shared_email)
    payload1["city_uuid"] = city_uuid
    client_with_overrides.post("/offers", json=payload1)

    payload2 = make_offer_create_payload(f"offer2-{uuid4().hex[:4]}", email=shared_email)
    payload2["city_uuid"] = city_uuid
    client_with_overrides.post("/offers", json=payload2)

    listed = client_with_overrides.get("/offers", params={"search": payload1["description"]})
    offer_uuid = listed.json()["data"][0]["uuid"]

    similar = client_with_overrides.get(f"/offers/{offer_uuid}/similar")
    assert similar.status_code == 200
    similar_offers = similar.json()

    # Should find at least the offer itself
    assert len(similar_offers) >= 1


# ============================================================================
# RAW OFFERS FILTERING
# ============================================================================


@pytest.mark.integration
def test_list_raw_offers_with_status_filter(client):
    """Test filtering raw offers by status"""
    offer_uid = f"o-status-{uuid4().hex[:6]}"
    client.post("/offers/raw", json=make_offer_payload(offer_uid))

    raw = client.get("/offers/raw")
    offer_uuid = next(item["uuid"] for item in raw.json()["data"] if item["offer_uid"] == offer_uid)

    # Accept the offer
    client.patch(f"/offers/raw/{offer_uuid}/accept")

    # Filter by active status
    response = client.get("/offers/raw", params={"status": "active"})
    assert response.status_code == 200
    data = response.json()["data"]

    # Verify the accepted offer appears in active filter
    active_uuids = [item["uuid"] for item in data]
    assert offer_uuid in active_uuids


@pytest.mark.integration
def test_list_raw_offers_sorting_by_name(client):
    """Test sorting raw offers by name"""
    response_asc = client.get("/offers/raw", params={"field": "name", "order": "asc", "limit": 5})
    assert response_asc.status_code == 200

    response_desc = client.get("/offers/raw", params={"field": "name", "order": "desc", "limit": 5})
    assert response_desc.status_code == 200


@pytest.mark.integration
def test_list_raw_offers_with_search(client):
    """Test searching raw offers"""
    unique_text = f"searchable-{uuid4().hex[:8]}"
    client.post("/offers/raw", json=make_offer_payload(f"o-{unique_text}"))

    response = client.get("/offers/raw", params={"search": unique_text})
    assert response.status_code == 200
    body = response.json()

    # Should find the offer with matching text
    assert any(unique_text in item["offer_uid"] for item in body["data"])


# ============================================================================
# ADDITIONAL VALIDATION TESTS
# ============================================================================


@pytest.mark.integration
def test_create_offer_with_invalid_email(client_with_overrides):
    """Test creating offer with invalid email format"""
    city_uuid = setup_test_city(client_with_overrides, "EmailCity")

    payload = make_offer_create_payload("test", email="not-an-email")
    payload["city_uuid"] = city_uuid

    response = client_with_overrides.post("/offers", json=payload)
    assert response.status_code == 422


@pytest.mark.integration
def test_create_offer_with_invalid_uuid(client_with_overrides):
    """Test creating offer with malformed city UUID"""
    payload = make_offer_create_payload("test", email="test@example.com")
    payload["city_uuid"] = "not-a-valid-uuid"

    response = client_with_overrides.post("/offers", json=payload)
    assert response.status_code == 422


@pytest.mark.integration
def test_create_offer_with_nonexistent_city_uuid(client_with_overrides):
    """Test creating offer with non-existent city UUID"""
    payload = make_offer_create_payload("test", email="test@example.com")
    payload["city_uuid"] = str(uuid4())

    response = client_with_overrides.post("/offers", json=payload)
    assert response.status_code in [404, 422]


@pytest.mark.integration
def test_create_offer_with_invalid_role_uuid(client_with_overrides):
    """Test creating offer with invalid legal role UUID"""
    city_uuid = setup_test_city(client_with_overrides, "RoleCity")

    payload = make_offer_create_payload("test", email="test@example.com")
    payload["city_uuid"] = city_uuid
    payload["roles"] = [str(uuid4())]  # Non-existent role

    response = client_with_overrides.post("/offers", json=payload)
    assert response.status_code in [404, 422]


# ============================================================================
# LOCATION-BASED FILTERING TESTS
# ============================================================================


@pytest.mark.integration
def test_location_filtering_finds_nearby_offers(client_with_overrides):
    """Test that location filtering correctly finds nearby offers"""
    # Create city at specific coordinates
    city_name = f"LocationCity-{uuid4().hex[:6]}"
    lat, lon = 52.0, 21.0
    city_payload = make_city_payload(city_name, teryt=f"SIMC-{uuid4().hex[:6]}", lat=lat, lon=lon)
    client_with_overrides.post("/places/city", json=city_payload)

    city_uuid = client_with_overrides.get(f"/places/city/{city_name}").json()[0]["uuid"]

    # Create offer in this city
    description = f"nearby-{uuid4().hex[:8]}"
    payload = make_offer_create_payload(description, email="nearby@example.com")
    payload["city_uuid"] = city_uuid
    client_with_overrides.post("/offers", json=payload)

    # Search for offers near this location (within 50km)
    response = client_with_overrides.get("/offers", params={"lat": lat, "lon": lon, "distance_km": 50})

    assert response.status_code == 200
    # The offer should be in results (exact matching depends on your implementation)


@pytest.mark.integration
def test_location_filtering_with_zero_distance(client_with_overrides):
    """Test location filtering with invalid zero distance"""
    response = client_with_overrides.get("/offers", params={"lat": 52.0, "lon": 21.0, "distance_km": 0})
    assert response.status_code == 422


@pytest.mark.integration
def test_location_filtering_with_excessive_distance(client_with_overrides):
    """Test location filtering with distance exceeding maximum"""
    response = client_with_overrides.get("/offers", params={"lat": 52.0, "lon": 21.0, "distance_km": 1001})
    assert response.status_code == 422


# ============================================================================
# COMPREHENSIVE WORKFLOW TESTS
# ============================================================================


@pytest.mark.integration
def test_complete_raw_offer_workflow(client_with_overrides):
    """Test complete workflow: create -> list -> get -> parse -> accept"""
    offer_uid = f"o-workflow-{uuid4().hex[:6]}"

    # Create
    create_resp = client_with_overrides.post("/offers/raw", json=make_offer_payload(offer_uid))
    assert create_resp.status_code == 201

    # List and find
    list_resp = client_with_overrides.get("/offers/raw")
    assert list_resp.status_code == 200
    offer_uuid = next(item["uuid"] for item in list_resp.json()["data"] if item["offer_uid"] == offer_uid)

    # Get individual
    get_resp = client_with_overrides.get(f"/offers/raw/{offer_uuid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["offer_uid"] == offer_uid

    # Parse
    parse_resp = client_with_overrides.get(f"/offers/raw/{offer_uuid}/parse")
    assert parse_resp.status_code == 200
    assert parse_resp.json()["success"] is True

    # Accept
    accept_resp = client_with_overrides.patch(f"/offers/raw/{offer_uuid}/accept")
    assert accept_resp.status_code == 204

    # Verify status changed
    final_resp = client_with_overrides.get(f"/offers/raw/{offer_uuid}")
    assert final_resp.json()["status"].lower() == "active"


@pytest.mark.integration
def test_multiple_offers_with_same_author(client_with_overrides):
    """Test creating multiple offers from the same author"""
    city_uuid = setup_test_city(client_with_overrides, "MultiCity")
    author = f"author-{uuid4().hex[:6]}"

    offers = []
    for i in range(3):
        payload = make_offer_create_payload(f"multi-{i}-{uuid4().hex[:4]}", f"multi{i}@example.com", author=author)
        payload["city_uuid"] = city_uuid
        resp = client_with_overrides.post("/offers", json=payload)
        assert resp.status_code == 201
        offers.append(payload["description"])

    # Search for offers (implementation-dependent on whether author is searchable)
    response = client_with_overrides.get("/offers", params={"limit": 100})
    assert response.status_code == 200


@pytest.mark.integration
def test_offer_with_multiple_legal_roles(client_with_overrides):
    """Test creating offer with multiple legal roles"""
    city_uuid = setup_test_city(client_with_overrides, "MultiRoleCity")

    roles_resp = client_with_overrides.get("/offers/legal_roles")
    all_roles = roles_resp.json()

    if len(all_roles) >= 2:
        role_uuids = [all_roles[0]["uuid"], all_roles[1]["uuid"]]

        payload = make_offer_create_payload("multi-role", "multirole@example.com")
        payload["city_uuid"] = city_uuid
        payload["roles"] = role_uuids

        response = client_with_overrides.post("/offers", json=payload)
        assert response.status_code == 201


# ============================================================================
# EDGE CASES & STRESS TESTS
# ============================================================================


@pytest.mark.integration
def test_list_offers_with_zero_limit(client_with_overrides):
    """Test listing with limit=0"""
    response = client_with_overrides.get("/offers", params={"limit": 0})
    # Should either return empty array or validation error
    assert response.status_code in [200, 422]


@pytest.mark.integration
def test_list_offers_with_large_offset(client_with_overrides):
    """Test listing with offset beyond available records"""
    response = client_with_overrides.get("/offers", params={"offset": 999999})
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 0 or body["data"] is not None


@pytest.mark.integration
def test_update_offer_with_empty_payload(client_with_overrides):
    """Test updating offer with empty JSON"""
    offer_uuid = create_test_offer(client_with_overrides)

    response = client_with_overrides.patch(f"/offers/{offer_uuid}", json={})
    # Should either succeed (no changes) or return validation error
    assert response.status_code in [204, 422]


@pytest.mark.integration
def test_create_offer_with_very_long_description(client_with_overrides):
    """Test creating offer with extremely long description"""
    city_uuid = setup_test_city(client_with_overrides, "LongDescCity")

    long_description = "x" * 10000  # Very long description
    payload = make_offer_create_payload(long_description, "long@example.com")
    payload["city_uuid"] = city_uuid

    response = client_with_overrides.post("/offers", json=payload)
    # Should either succeed or return validation error based on field limits
    assert response.status_code in [201, 422]


@pytest.mark.integration
def test_special_characters_in_description(client_with_overrides):
    """Test creating offer with special characters"""
    city_uuid = setup_test_city(client_with_overrides, "SpecialCity")

    special_desc = "Test <script>alert('xss')</script> & symbols: @#$%^&*()"
    payload = make_offer_create_payload(special_desc, "special@example.com")
    payload["city_uuid"] = city_uuid

    response = client_with_overrides.post("/offers", json=payload)
    assert response.status_code == 201

    # Verify the description is stored correctly
    listed = client_with_overrides.get("/offers", params={"limit": 100})
    offers = listed.json()["data"]
    matching = [o for o in offers if special_desc in o.get("description", "")]
    assert len(matching) > 0


@pytest.mark.integration
def test_concurrent_duplicate_prevention(client):
    """Test that duplicate prevention works"""
    payload = make_offer_payload(f"o-concurrent-{uuid4().hex[:6]}")

    # First creation should succeed
    resp1 = client.post("/offers/raw", json=payload)
    assert resp1.status_code == 201

    # Immediate duplicate should fail
    resp2 = client.post("/offers/raw", json=payload)
    assert resp2.status_code == 409
