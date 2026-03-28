from datetime import UTC, datetime, timedelta

import pytest

from app.utils.timestamp_utils import extract_timestamp_from_filename


@pytest.mark.parametrize("filename, expected", [
    ("20250819_110812.json", datetime(2025, 8, 19, 11, 8, 12)),
    ("report-foo_20240102_030405_backup.json", datetime(2024, 1, 2, 3, 4, 5)),
])
def test_extract_timestamp_from_filename_parses_correctly(filename, expected):
    # When
    dt = extract_timestamp_from_filename(filename)

    # Then
    assert isinstance(dt, datetime)
    # Parsed result is naive datetime according to implementation
    assert dt.tzinfo is None
    assert dt == expected


@pytest.mark.parametrize("filename", [
    "no-timestamp-here.json",
    "data.txt",
    "",
])
def test_extract_timestamp_missing_pattern_returns_aware_now(filename):
    # Given
    before = datetime.now(UTC)

    # When
    dt = extract_timestamp_from_filename(filename)
    after = datetime.now(UTC)

    # Then
    # Should be timezone-aware in UTC
    assert dt.tzinfo is UTC
    # And should be between before and after
    assert before <= dt <= after


def test_extract_timestamp_handles_bad_input_types():
    # Given
    before = datetime.now(UTC)

    # When
    dt = extract_timestamp_from_filename(None)  # type: ignore[arg-type]
    after = datetime.now(UTC)

    # Then
    assert dt.tzinfo is UTC
    # Allow a small delta; ensure it's close to now
    assert before <= dt <= after + timedelta(seconds=1)
