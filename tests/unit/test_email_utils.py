
import pytest

from app.utils.email_utils import (
    apply_simple_fixes,
    extract_and_fix_email,
    try_extract_email,
)


def test_extract_and_fix_email_basic_extraction_and_lowercase():
    text = "Please contact John <John.Doe+Tag@Example.COM> about the issue."
    out = extract_and_fix_email(text)
    assert out == "john.doe+tag@example.com"


def test_extract_and_fix_email_trailing_junk_after_tld_removed():
    text = "email: user@domain.comxyz more text"
    out = extract_and_fix_email(text)
    assert out == "user@domain.com"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("12.user@domain.plabc", "user@domain.pl"),  # numeric prefix and trailing junk
        ("user@school.edu.plX", "user@school.edu.pl"),  # multi-part known TLD
        ("person@ngo.org.pl_", "person@ngo.org.pl"),  # underscore after tld
        ("corp@net.com.pl123", "corp@net.com.pl"),
    ],
)
def test_apply_simple_fixes_known_tlds_and_prefix_cleanup(raw, expected):
    fixed = apply_simple_fixes(raw)
    # after applying fixes, try_extract_email should see the corrected address
    assert try_extract_email(fixed) == expected


def test_extract_and_fix_email_non_string_returns_none():
    assert extract_and_fix_email(None) is None
    assert extract_and_fix_email(12345) is None  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("team <team@foo.org>", "team@foo.org"),  # other TLD accepted by regex 2-4 letters
        ("support@mail.net", "support@mail.net"),
    ],
)
def test_try_extract_email_accepts_various_2_to_4_letter_tlds(text, expected):
    assert try_extract_email(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "no email here",
        "broken@email",  # no tld
        "user@domain.museum",  # tld longer than 4 should be rejected by try_extract_email
    ],
)
def test_try_extract_email_rejects_invalid(text):
    assert try_extract_email(text) is None


def test_apply_simple_fixes_does_not_overclean_valid_email():
    original = "valid.user@ok.com"
    fixed = apply_simple_fixes(original)
    assert fixed == original
    assert extract_and_fix_email(original) == original
