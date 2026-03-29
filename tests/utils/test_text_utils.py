from datetime import datetime

import pytest

from app.common.text_utils import (
    generate_offer_management_token,
    remove_html_tags,
    sanitize_and_normalize_text,
    sanitize_name,
    split_street,
)


def test_should_generate_consistent_offer_management_token():
    # Given
    offer_uuid = "123e4567-e89b-12d3-a456-426614174000"
    created_at = datetime(2025, 1, 1, 12, 0, 0)

    # When
    token1 = generate_offer_management_token(offer_uuid, created_at)
    token2 = generate_offer_management_token(offer_uuid, created_at)

    # Then
    # Same inputs should produce same token
    assert token1 == token2
    assert len(token1) == 64  # SHA-256 hex digest length

    # When
    # Different UUID should produce different token
    token3 = generate_offer_management_token("different-uuid", created_at)

    # Then
    assert token1 != token3

    # When
    # Different created_at should produce different token
    created_at2 = datetime(2025, 1, 1, 12, 0, 1)
    token4 = generate_offer_management_token(offer_uuid, created_at2)

    # Then
    assert token1 != token4


@pytest.mark.parametrize("html, expected", [
    ("Hello <b>World</b>!", "Hello World!"),
    ("<p>Test</p>", "Test"),
    ("No HTML", "No HTML"),
])
def test_should_remove_html_tags(html, expected):
    # When
    result = remove_html_tags(html)

    # Then
    assert result == expected


@pytest.mark.parametrize("raw, expected", [
    ("  Hello\u00A0\tWorld\n\r\nThis   is  “quoted”  text  ", 'Hello World This is "quoted" text'),
    ("<p>‘Ala’ i “kot”</p>", "'Ala' i \"kot\""),
])
def test_should_sanitize_and_normalize_text(raw, expected):
    # When
    result = sanitize_and_normalize_text(raw)

    # Then
    assert result == expected


@pytest.mark.parametrize("name, expected", [
    ("Zażółć gęślą jaźń!  Foo — Bar  & Baz", "zazolc-gesla-jazn-foo-bar-baz"),
    ("  ---Hello   World---  ", "hello-world"),
    ("Simple Name", "simple-name"),
])
def test_should_sanitize_name_correctly(name, expected):
    # When
    result = sanitize_name(name)

    # Then
    assert result == expected


@pytest.mark.parametrize("street_input, expected_street, expected_number", [
    ("Marszałkowska 22", "Marszałkowska", "22"),
    ("Wspólna 4d", "Wspólna", "4d"),
    ("Aleje Jerozolimskie 18 a", "Aleje Jerozolimskie", "18a"),
    ("Hoża 25/2a", "Hoża", "25/2a"),
    ("Krakowskie Przedmieście 12-13", "Krakowskie Przedmieście", "12-13"),
    ("Nowy Świat 23, 25a/2", "Nowy Świat", "23,25a/2"),
    ("Pola Mokotowskie", "Pola Mokotowskie", None),
    ("Street 123B/45", "Street", "123B/45"),
])
def test_should_split_street_correctly(street_input, expected_street, expected_number):
    # When
    result = split_street(street_input)

    # Then
    assert result == (expected_street, expected_number)
