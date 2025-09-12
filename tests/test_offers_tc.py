from datetime import datetime, timezone

import pytest


# def make_offer_payload(uid: str, author: str = "john", author_uid: str = "u1") -> dict:
#     return {
#         "raw_data": "Some raw offer text about case in court",
#         "author": author,
#         "author_uid": author_uid,
#         "offer_uid": uid,
#         "timestamp": datetime.now(timezone.utc).isoformat(),
#         "source": "bot",
#     }
#
#
# @pytest.mark.integration
# def test_create_and_list_raw_offers(client):
#     # create two offers
#     r1 = client.post("/offers/raw", json=make_offer_payload("o-1"))
#     assert r1.status_code == 201
#
#     r2 = client.post("/offers/raw", json=make_offer_payload("o-2", author="alice", author_uid="u2"))
#     assert r2.status_code == 201
#
#     # list
#     res = client.get("/offers/raw", params={"limit": 10, "offset": 0, "order": "asc", "field": "created_at"})
#     assert res.status_code == 200
#     body = res.json()
#
#     assert body["count"] == 2
#     assert body["limit"] == 10
#     assert body["offset"] == 0
#     assert len(body["data"]) == 2
#
#     # Ensure important fields exist
#     item = body["data"][0]
#     assert {"uuid", "author", "author_uid", "offer_uid", "raw_data", "source", "added_at"}.issubset(item.keys())
#
#
# @pytest.mark.integration
# def test_duplicate_offer_returns_409(client):
#     payload = make_offer_payload("o-dup")
#
#     r1 = client.post("/offers/raw", json=payload)
#     assert r1.status_code == 201
#
#     r2 = client.post("/offers/raw", json=payload)
#     assert r2.status_code == 409
#     assert "already exists" in r2.json()["detail"]
#
#
# @pytest.mark.integration
# def test_read_only_accepted_offers(client):
#     # create new offer
#     client.post("/offers/raw", json=make_offer_payload("o-acc"))
#
#     # fetch its uuid from raw list
#     raw = client.get("/offers/raw")
#     uuids = [item["uuid"] for item in raw.json()["data"] if item["offer_uid"] == "o-acc"]
#     assert uuids, "Newly created offer should be retrievable"
#     offer_uuid = uuids[0]
#
#     # update status to accepted
#     patch = client.patch(f"/offers/parse/{offer_uuid}", json={"status": "accepted"})
#     assert patch.status_code == 204
#
#     # /offers endpoint should return only accepted offers
#     res = client.get("/offers", params={"limit": 10, "offset": 0})
#     assert res.status_code == 200
#     body = res.json()
#     # Find our offer in accepted list
#     uids = [item["uuid"] for item in body["data"]]
#     assert offer_uuid in uids
