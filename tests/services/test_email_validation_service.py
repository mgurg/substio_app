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


def test_should_send_offer_email_returns_true_in_prod(email_validator, prod_settings):
    updated_offer, original_offer = _make_offers()

    result = email_validator.should_send_offer_email(
        updated_offer=updated_offer,
        original_offer=original_offer,
        submit_email=True,
    )

    assert result is True


def test_should_send_offer_email_requires_email(email_validator, prod_settings):
    updated_offer, original_offer = _make_offers(email=None)

    result = email_validator.should_send_offer_email(
        updated_offer=updated_offer,
        original_offer=original_offer,
        submit_email=True,
    )

    assert result is False


def test_should_send_offer_email_requires_prod(email_validator, monkeypatch):
    monkeypatch.setattr(
        email_validator,
        "settings",
        MagicMock(APP_ENV="DEV"),
        raising=True,
    )
    updated_offer, original_offer = _make_offers()

    result = email_validator.should_send_offer_email(
        updated_offer=updated_offer,
        original_offer=original_offer,
        submit_email=True,
    )

    assert result is False


def test_should_send_offer_email_requires_submit_email(email_validator, prod_settings):
    updated_offer, original_offer = _make_offers()

    result = email_validator.should_send_offer_email(
        updated_offer=updated_offer,
        original_offer=original_offer,
        submit_email=False,
    )

    assert result is False


def test_should_send_offer_email_requires_active_status(email_validator, prod_settings):
    updated_offer, original_offer = _make_offers(status=OfferStatus.NEW)

    result = email_validator.should_send_offer_email(
        updated_offer=updated_offer,
        original_offer=original_offer,
        submit_email=True,
    )

    assert result is False


def test_should_send_user_offer_creation_email_returns_true_in_prod(email_validator, prod_settings):
    offer = MagicMock(spec=Offer, email="test@example.com", status=OfferStatus.ACTIVE, source=SourceType.USER, uuid="test-uuid")

    result = email_validator.should_send_user_offer_creation_email(
        offer=offer
    )

    assert result is True


def test_should_send_user_offer_creation_email_requires_user_source(email_validator, prod_settings):
    offer = MagicMock(spec=Offer, email="test@example.com", status=OfferStatus.ACTIVE, source=SourceType.BOT, uuid="test-uuid")

    result = email_validator.should_send_user_offer_creation_email(
        offer=offer
    )

    assert result is False


def test_should_send_user_offer_creation_email_requires_active_status(email_validator, prod_settings):
    offer = MagicMock(spec=Offer, email="test@example.com", status=OfferStatus.NEW, source=SourceType.USER, uuid="test-uuid")

    result = email_validator.should_send_user_offer_creation_email(
        offer=offer
    )

    assert result is False


def test_should_send_user_offer_creation_email_requires_prod(email_validator, monkeypatch):
    monkeypatch.setattr(
        email_validator,
        "settings",
        MagicMock(APP_ENV="DEV"),
        raising=True,
    )
    offer = MagicMock(spec=Offer, email="test@example.com", status=OfferStatus.ACTIVE, source=SourceType.USER, uuid="test-uuid")

    result = email_validator.should_send_user_offer_creation_email(
        offer=offer
    )

    assert result is False
