import re

VALID_TLDS = ["pl", "com", "eu", "org.pl", "net.pl", "com.pl"]
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def extract_and_fix_email(text: str) -> str | None:
    """
    Extract and normalize email addresses from text.

    Handles common issues like trailing junk after TLDs and numeric prefixes.
    """
    if not isinstance(text, str):
        return None

    email = _extract_email_candidate(text)
    if not email:
        return None
    cleaned = _clean_email(email)
    return _extract_email_candidate(cleaned)


def _extract_email_candidate(text: str) -> str | None:
    """
    Extract the first email-like string from text and validate the basic structure.
    """
    match = EMAIL_PATTERN.search(text)
    if not match:
        return None

    email = match.group(0).lower()

    # Validate: must have @ and end with 2-5 letter TLD
    if "@" not in email:
        return None

    if not re.search(r"\.[a-z]{2,5}$", email):
        return None

    return email


def _clean_email(email: str) -> str:
    """
    Remove common artifacts from extracted email strings.

    Fixes:
    - Trailing junk after known TLDs (e.g., ".comxyz" -> ".com")
    - Leading numeric prefixes (e.g., "12.user@" -> "user@")
    """
    # Remove trailing junk after known TLDs
    # Sort by length (longest first) to match multi-part TLDs like "edu.pl" before "pl"
    for tld in sorted(VALID_TLDS, key=len, reverse=True):
        pattern = rf"(\.{re.escape(tld)})([a-zA-Z0-9_]+)\b"
        email = re.sub(pattern, r"\1", email, flags=re.IGNORECASE)

    email = re.sub(r"^\d+\.", "", email)

    return email
