import re
from datetime import datetime
from pathlib import Path

TIMESTAMP_PATTERN = re.compile(r"(\d{8})_(\d{6})")


def extract_timestamp_from_filename(filename: str) -> datetime:
    """
    Extract timestamp from filename format: YYYYMMDD_HHMMSS.json
    Example: 20250819_110812.json -> 2025-08-19 11:08:12

    Falls back to the current datetime if parsing fails.

    Args:
        filename: Filename containing timestamp pattern

    Returns:
        datetime: Extracted timestamp or current datetime if parsing fails
    """
    try:
        base_name = Path(filename).stem
        match = TIMESTAMP_PATTERN.search(base_name)
        if not match:
            return datetime.now()

        return datetime.strptime(
            f"{match.group(1)}_{match.group(2)}", "%Y%m%d_%H%M%S"
        )
    except Exception:
        return datetime.now()
