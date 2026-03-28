from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.core.dependencies import get_email_notifier
from app.infrastructure.notifications.email.email_notifier_base import EmailNotifierBase
from tests.utils.test_helpers import make_offer_create_payload, setup_test_city


@pytest.fixture
def mock_email_notifier(client):
    mock = AsyncMock(spec=EmailNotifierBase)
    # Mock send methods to return True (success)
    mock.send_user_offer_created_email.return_value = True
    mock.send_offer_imported_email.return_value = True

    client.app.dependency_overrides[get_email_notifier] = lambda: mock
    try:
        yield mock
    finally:
        client.app.dependency_overrides.pop(get_email_notifier, None)


@pytest.fixture
def prod_env(client, monkeypatch):
    settings = get_settings()
    # We monkeypatch the settings instance which is a singleton and used by services
    monkeypatch.setattr(settings, "APP_ENV", "PROD")

    # We also need to ensure that the EmailValidationService uses the patched settings.
    # Since our get_email_validator dependency now calls get_settings(), it should
    # pick up the patched singleton.

    yield settings


@pytest.mark.integration
def test_user_offer_creation_triggers_email_in_prod(client, mock_email_notifier, prod_env):
    """
    Test that creating an offer with source=USER triggers an email notification when in PROD.
    """
    # Given
    city_uuid = setup_test_city(client, "EmailProdCity")
    description = f"test-email-flow-{uuid4().hex[:8]}"
    email = "user@example.com"
    payload = make_offer_create_payload(description, email=email)
    payload["city_uuid"] = city_uuid
    payload["source"] = "user"
    payload.update({"date_str": "2026-12-01", "hour_str": "12:00", "roles_uuids": []})

    # When
    response = client.post("/offers", json=payload)

    # Then
    assert response.status_code == 201
    assert mock_email_notifier.send_user_offer_created_email.called
    args, kwargs = mock_email_notifier.send_user_offer_created_email.call_args
    assert kwargs["recipient_email"] == email
    assert kwargs["offer_text"] == description
    assert "token" in kwargs
    assert len(kwargs["token"]) > 0


@pytest.mark.integration
def test_user_offer_creation_no_email_in_dev(client, mock_email_notifier):
    """
    Test that creating an offer with source=USER does NOT trigger an email notification when in DEV.
    """
    # Given
    # By default APP_ENV is DEV in tests (set in conftest.py)
    settings = get_settings()
    assert settings.APP_ENV == "DEV"

    city_uuid = setup_test_city(client, "EmailDevCity")
    description = f"test-no-email-dev-{uuid4().hex[:8]}"
    email = "user@example.com"
    payload = make_offer_create_payload(description, email=email)
    payload["city_uuid"] = city_uuid
    payload["source"] = "user"
    payload.update({"date_str": "2026-12-01", "hour_str": "12:00", "roles_uuids": []})

    # When
    response = client.post("/offers", json=payload)

    # Then
    assert response.status_code == 201
    assert not mock_email_notifier.send_user_offer_created_email.called


@pytest.mark.integration
def test_imported_offer_patch_triggers_email_in_prod(client, mock_email_notifier, prod_env):
    """
    Test that updating an imported (BOT) offer with submit_email=True triggers an email in PROD.
    """
    # Given
    # 1. Create a BOT offer first (imported raw offer)
    offer_uid = f"bot-offer-{uuid4().hex[:8]}"
    email = "bot-user@example.com"
    raw_payload = {
        "raw_data": f"Imported offer text with email {email}",
        "author": "Bot",
        "author_uid": "bot-1",
        "offer_uid": offer_uid,
        "source": "bot",
        "timestamp": "2026-03-15T12:00:00Z",
    }
    res = client.post("/offers/raw", json=raw_payload)
    assert res.status_code == 201

    # Get the UUID of the created raw offer
    raw_list = client.get("/offers/raw", params={"search": offer_uid})
    data = raw_list.json()["data"]
    offer_uuid = data[0]["uuid"]

    # 2. Update/Patch data
    city_uuid = setup_test_city(client, "PatchCity")
    update_payload = {
        "description": "Updated description",
        "city_uuid": city_uuid,
        "submit_email": True,
        "status": "active",
        "date_str": "2026-12-01",
        "hour_str": "12:00",
        "roles_uuids": [],
    }

    # When
    response = client.patch(f"/offers/{offer_uuid}", json=update_payload)

    # Then
    assert response.status_code == 204
    assert mock_email_notifier.send_offer_imported_email.called
    args, kwargs = mock_email_notifier.send_offer_imported_email.call_args
    assert kwargs["recipient_email"] == email
    assert kwargs["offer_uuid"] == str(offer_uuid)
