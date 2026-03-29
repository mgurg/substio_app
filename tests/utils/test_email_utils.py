from datetime import UTC, datetime, timedelta

import pytest

from app.utils.timestamp_utils import extract_timestamp_from_filename


def test_should_successfully_extract_timestamp_from_simple_filename():
    dt = extract_timestamp_from_filename("20250819_110812.json")
    assert isinstance(dt, datetime)
    # Parsed result is naive datetime according to implementation
    assert dt.tzinfo is None
    assert dt == datetime(2025, 8, 19, 11, 8, 12)


def test_should_successfully_extract_timestamp_from_filename_with_prefix_and_suffix():
    dt = extract_timestamp_from_filename("report-foo_20240102_030405_backup.json")
    assert dt == datetime(2024, 1, 2, 3, 4, 5)
    assert dt.tzinfo is None


@pytest.mark.parametrize("filename", [
    "no-timestamp-here.json",
    "data.txt",
    "",
])
def test_should_return_now_when_extracting_timestamp_from_filename_without_pattern(filename):
    before = datetime.now(UTC)
    dt = extract_timestamp_from_filename(filename)
    after = datetime.now(UTC)

    # Should be timezone-aware in UTC
    assert dt.tzinfo is UTC
    # And should be between before and after
    assert before <= dt <= after


def test_should_handle_bad_input_types_when_extracting_timestamp():
    before = datetime.now(UTC)
    dt = extract_timestamp_from_filename(None)  # type: ignore[arg-type]
    after = datetime.now(UTC)

    assert dt.tzinfo is UTC
    # Allow a small delta; ensure it's close to now
    assert before <= dt <= after + timedelta(seconds=1)
