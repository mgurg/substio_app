import hashlib
import hmac
import re
import unicodedata
from datetime import datetime

from unidecode import unidecode

from app.core.config import get_settings

settings = get_settings()


def generate_offer_management_token(offer_uuid: str, created_at: datetime) -> str:
    """
    Generate a secure token for offer management based on UUID and created_at date.
    Uses HMAC-SHA256 with APP_SECRET_KEY.
    """
    secret = settings.APP_SECRET_KEY.encode()
    # Using ISO format with microseconds for better uniqueness
    message = f"{offer_uuid}:{created_at.isoformat()}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def remove_html_tags(text):
    html_pattern = re.compile("<.*?>")
    clean_text = re.sub(html_pattern, "", text)
    return clean_text


# Extended Latin script regex (allowing all punctuation marks, emojis, and symbols)
def sanitize_and_normalize_text(input_text: str) -> str:
    """
    Sanitizes and normalizes the input text by:
    - Ensuring it contains only allowed characters (extended Latin script, emojis, all punctuation marks).
    - Normalizing Unicode (e.g., combining characters to their canonical forms).
    - Trimming extra whitespace.
    - Standardizing punctuation.
    - Collapsing all types of spaces to a single regular space.
    - Normalizing all types of newlines to a single form (e.g., '\n').

    :param input_text: The text to sanitize and normalize.
    :return: Sanitized and normalized text.
    :raises ValueError: If text contains invalid characters.
    """

    no_html_text = remove_html_tags(input_text)
    # Normalize Unicode (canonical decomposition)
    normalized_text = unicodedata.normalize("NFC", no_html_text)

    # Normalize all types of spaces to a single regular space (including non-breaking space)
    normalized_text = re.sub(r"[\s\u00A0]+", " ", normalized_text)

    # Normalize newlines to a single form (e.g., '\n')
    normalized_text = re.sub(r"[\r\n]+", "\n", normalized_text)

    # Trim leading/trailing spaces
    normalized_text = normalized_text.strip()

    # Replace fancy quotes with standard quotes
    normalized_text = normalized_text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

    return normalized_text


def sanitize_name(input_str: str) -> str:
    """
    Sanitize string to make it URL-safe.
    Remove non-alphanumeric characters, replace spaces with hyphens,
    and handle duplicate or leading/trailing hyphens.
    """
    # Transliterate Unicode characters to ASCII
    safe_name = unidecode(input_str)

    # Replace non-alphanumeric characters (except hyphens) with spaces
    cleaned_str = re.sub(r"[^a-zA-Z0-9\s-]", " ", safe_name)

    # Replace spaces with hyphens, collapse multiple spaces/hyphens into one
    hyphenated_str = re.sub(r"[\s-]+", "-", cleaned_str).lower()

    # Remove leading and trailing hyphens
    return hyphenated_str.strip("-")


def split_street(street: str) -> tuple[str, str | None]:
    """
    Splits a street string into (street_name, street_number).
    Handles Polish-style house numbers with letters, slashes, commas, and ranges.
    Normalizes street_number (removes internal spaces).
    """
    pattern = (
        r"\s("
        r"\d+\s*[A-Za-z]?"  # 22, 4d, 18 a
        r"(?:[-/]\d+\s*[A-Za-z]?)*"  # -13, /25, /2a, -13B
        r"(?:,\s*\d+\s*[A-Za-z]?(?:[-/]\d+\s*[A-Za-z]?)*?)*"  # , 23, , 25a/2, , 12-13
        r")$"
    )

    match = re.search(pattern, street)
    if match:
        street_number = re.sub(r"\s+", "", match.group(1))  # normalize: remove spaces
        street_name = street[: match.start(1)].strip()
    else:
        street_name = street.strip()
        street_number = None
    return street_name, street_number
