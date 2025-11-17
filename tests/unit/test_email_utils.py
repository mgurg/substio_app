
import pytest

from app.utils.email_utils import (
    _clean_email,
    _extract_email_candidate,
    extract_and_fix_email,
)


@pytest.mark.parametrize(
    "text, expected",
    [
        pytest.param(
            "Please contact John <John.Doe+Tag@Example.COM> about the issue.",
            "john.doe+tag@example.com",
            id="basic_extraction_and_lowercase",
        ),
        pytest.param(
            "email: user@domain.comx more text",
            "user@domain.com",
            id="trailing_junk_after_tld_removed",
        ),
        pytest.param(
            "adres e-mail: jan.kowalski@abtla.euZ wyrazami szacunku",
            "jan.kowalski@abtla.eu",
            id="eu_domain_with_trailing_char",
        ),
    ],
)
def test_extract_and_fix_email(text, expected):
    out = extract_and_fix_email(text)
    assert out == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("12.user@domain.plabc", "user@domain.pl"),  # numeric prefix and trailing junk
        ("user@school.edu.plX", "user@school.edu.pl"),  # multi-part known TLD
        ("person@ngo.org.pl_", "person@ngo.org.pl"),  # underscore after tld
        ("corp@net.com.pl123", "corp@net.com.pl"),
        ("jan.kowalski@btla.euZ", "jan.kowalski@btla.eu"),
    ],
)
def test_clean_email_known_tlds_and_prefix_cleanup(raw, expected):
    fixed = _clean_email(raw)
    # after applying fixes, _extract_email_candidate should see the corrected address
    assert _extract_email_candidate(fixed) == expected


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
def test_extract_email_candidate_accepts_various_2_to_5_letter_tlds(text, expected):
    assert _extract_email_candidate(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "no email here",
        "broken@email",  # no tld
        "user@domain.museum",  # tld longer than 4 should be rejected by _extract_email_candidate
    ],
)
def test_extract_email_candidate_rejects_invalid(text):
    assert _extract_email_candidate(text) is None


def test_clean_email_does_not_overclean_valid_email():
    original = "valid.user@ok.com"
    fixed = _clean_email(original)
    assert fixed == original
    assert extract_and_fix_email(original) == original
