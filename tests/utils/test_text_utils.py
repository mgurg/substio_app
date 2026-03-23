
from datetime import datetime

from app.common.text_utils import (
    generate_offer_management_token,
    remove_html_tags,
    sanitize_and_normalize_text,
    sanitize_name,
    split_street,
)


def test_generate_offer_management_token():
    offer_uuid = "123e4567-e89b-12d3-a456-426614174000"
    created_at = datetime(2025, 1, 1, 12, 0, 0)

    token1 = generate_offer_management_token(offer_uuid, created_at)
    token2 = generate_offer_management_token(offer_uuid, created_at)

    # Same inputs should produce same token
    assert token1 == token2
    assert len(token1) == 64  # SHA-256 hex digest length

    # Different UUID should produce different token
    token3 = generate_offer_management_token("different-uuid", created_at)
    assert token1 != token3

    # Different created_at should produce different token
    created_at2 = datetime(2025, 1, 1, 12, 0, 1)
    token4 = generate_offer_management_token(offer_uuid, created_at2)
    assert token1 != token4


def test_remove_html_tags_simple():
    assert remove_html_tags("Hello <b>World</b>!") == "Hello World!"


def test_sanitize_and_normalize_text_spaces_and_newlines():
    raw = "  Hello\u00A0\tWorld\n\r\nThis   is  “quoted”  text  "
    out = sanitize_and_normalize_text(raw)
    assert out == 'Hello World This is "quoted" text'


def test_sanitize_and_normalize_text_strips_html_and_fancy_quotes():
    raw = "<p>‘Ala’ i “kot”</p>"
    out = sanitize_and_normalize_text(raw)
    assert out == "'Ala' i \"kot\""


def test_sanitize_name_transliteration_and_cleanup():
    # Accents should be removed and spaces/punctuation normalized to hyphens
    name = "Zażółć gęślą jaźń!  Foo — Bar  & Baz"
    out = sanitize_name(name)
    assert out == "zazolc-gesla-jazn-foo-bar-baz"


def test_sanitize_name_collapse_and_trim_hyphens():
    assert sanitize_name("  ---Hello   World---  ") == "hello-world"


def test_split_street():
    # Regular Polish address
    assert split_street("Marszałkowska 22") == ("Marszałkowska", "22")
    # House number with letter
    assert split_street("Wspólna 4d") == ("Wspólna", "4d")
    # House number with space and letter
    assert split_street("Aleje Jerozolimskie 18 a") == ("Aleje Jerozolimskie", "18a")
    # Number with slash
    assert split_street("Hoża 25/2a") == ("Hoża", "25/2a")
    # Number with dash/range
    assert split_street("Krakowskie Przedmieście 12-13") == ("Krakowskie Przedmieście", "12-13")
    # Comma-separated numbers
    assert split_street("Nowy Świat 23, 25a/2") == ("Nowy Świat", "23,25a/2")
    # No number
    assert split_street("Pola Mokotowskie") == ("Pola Mokotowskie", None)
    # Number with multi-part TLD-like suffix (not really applicable here, but testing regex robustness)
    assert split_street("Street 123B/45") == ("Street", "123B/45")
