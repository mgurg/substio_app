from types import SimpleNamespace

import pytest

import app.services.email_validation_service as email_validation_service_module
from app.database.models.enums import OfferStatus, SourceType


@pytest.fixture
def prod_settings(monkeypatch):
    monkeypatch.setattr(
        email_validation_service_module,
        "settings",
        SimpleNamespace(APP_ENV="PROD"),
        raising=True,
    )


def _make_offers(email="test@example.com", status=OfferStatus.ACTIVE, source=SourceType.BOT):
    updated_offer = SimpleNamespace(email=email, status=status)
    original_offer = SimpleNamespace(source=source)
    return updated_offer, original_offer


def test_should_send_offer_email_returns_true_in_prod(prod_settings):
    updated_offer, original_offer = _make_offers()

    result = email_validation_service_module.EmailValidationService.should_send_offer_email(
        updated_offer=updated_offer,
        original_offer=original_offer,
        submit_email=True,
    )

    assert result is True


def test_should_send_offer_email_requires_email(prod_settings):
    updated_offer, original_offer = _make_offers(email=None)

    result = email_validation_service_module.EmailValidationService.should_send_offer_email(
        updated_offer=updated_offer,
        original_offer=original_offer,
        submit_email=True,
    )

    assert result is False


def test_should_send_offer_email_requires_prod(monkeypatch):
    monkeypatch.setattr(
        email_validation_service_module,
        "settings",
        SimpleNamespace(APP_ENV="DEV"),
        raising=True,
    )
    updated_offer, original_offer = _make_offers()

    result = email_validation_service_module.EmailValidationService.should_send_offer_email(
        updated_offer=updated_offer,
        original_offer=original_offer,
        submit_email=True,
    )

    assert result is False


def test_should_send_offer_email_requires_submit_email(prod_settings):
    updated_offer, original_offer = _make_offers()

    result = email_validation_service_module.EmailValidationService.should_send_offer_email(
        updated_offer=updated_offer,
        original_offer=original_offer,
        submit_email=False,
    )

    assert result is False


def test_should_send_offer_email_requires_active_status(prod_settings):
    updated_offer, original_offer = _make_offers(status=OfferStatus.NEW)

    result = email_validation_service_module.EmailValidationService.should_send_offer_email(
        updated_offer=updated_offer,
        original_offer=original_offer,
        submit_email=True,
    )

    assert result is False


def test_should_send_offer_email_requires_bot_source(prod_settings):
    updated_offer, original_offer = _make_offers(source=SourceType.USER)

    result = email_validation_service_module.EmailValidationService.should_send_offer_email(
        updated_offer=updated_offer,
        original_offer=original_offer,
        submit_email=True,
    )

    assert result is False
