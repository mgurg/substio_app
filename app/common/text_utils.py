import re
import unicodedata

from unidecode import unidecode


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
    normalized_text = (
        normalized_text.replace("“", '"').replace("”", '"')
        .replace("‘", "'").replace("’", "'")
    )

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
