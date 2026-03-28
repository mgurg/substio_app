from unittest.mock import MagicMock

import pytest

from app.database.models.enums import OfferStatus, SourceType
from app.database.models.models import Offer


@pytest.fixture
def email_validator(monkeypatch):
    from app.services.email_validation_service import EmailValidationService
    return EmailValidationService()


@pytest.fixture
def prod_settings(email_validator, monkeypatch):
    monkeypatch.setattr(
        email_validator,
        "settings",
        MagicMock(APP_ENV="PROD"),
        raising=True,
    )


def _make_offers(email="test@example.com", status=OfferStatus.ACTIVE, source=SourceType.BOT):
    updated_offer = MagicMock(spec=Offer, email=email, status=status)
    original_offer = MagicMock(spec=Offer, source=source)
    return updated_offer, original_offer


@pytest.mark.parametrize("updated_email, updated_status, submit_email, expected", [
    ("test@example.com", OfferStatus.ACTIVE, True, True),
    (None, OfferStatus.ACTIVE, True, False),
    ("test@example.com", OfferStatus.ACTIVE, False, False),
    ("test@example.com", OfferStatus.NEW, True, False),
])
def test_should_send_offer_email_parametrized(email_validator, prod_settings, updated_email, updated_status, submit_email, expected):
    # Given
    updated_offer, original_offer = _make_offers(email=updated_email, status=updated_status)

    # When
    result = email_validator.should_send_offer_email(
        updated_offer=updated_offer,
        original_offer=original_offer,
        submit_email=submit_email,
    )

    # Then
    assert result is expected


def test_should_send_offer_email_requires_prod(email_validator, monkeypatch):
    # Given
    monkeypatch.setattr(
        email_validator,
        "settings",
        MagicMock(APP_ENV="DEV"),
        raising=True,
    )
    updated_offer, original_offer = _make_offers()

    # When
    result = email_validator.should_send_offer_email(
        updated_offer=updated_offer,
        original_offer=original_offer,
        submit_email=True,
    )

    # Then
    assert result is False


@pytest.mark.parametrize("email, status, source, expected", [
    ("test@example.com", OfferStatus.ACTIVE, SourceType.USER, True),
    ("test@example.com", OfferStatus.ACTIVE, SourceType.BOT, False),
    ("test@example.com", OfferStatus.NEW, SourceType.USER, False),
])
def test_should_send_user_offer_creation_email_parametrized(email_validator, prod_settings, email, status, source, expected):
    # Given
    offer = MagicMock(spec=Offer, email=email, status=status, source=source, uuid="test-uuid")

    # When
    result = email_validator.should_send_user_offer_creation_email(
        offer=offer
    )

    # Then
    assert result is expected


def test_should_send_user_offer_creation_email_requires_prod(email_validator, monkeypatch):
    # Given
    monkeypatch.setattr(
        email_validator,
        "settings",
        MagicMock(APP_ENV="DEV"),
        raising=True,
    )
    offer = MagicMock(spec=Offer, email="test@example.com", status=OfferStatus.ACTIVE, source=SourceType.USER, uuid="test-uuid")

    # When
    result = email_validator.should_send_user_offer_creation_email(
        offer=offer
    )

    # Then
    assert result is False
