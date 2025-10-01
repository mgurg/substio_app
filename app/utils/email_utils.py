import re

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def extract_and_fix_email(text: str) -> str | None:
    """
    Extract email from text with simple domain fixing for .pl and .com

    Args:
        text: Raw text that might contain an email

    Returns:
        Valid email string or None if no valid email found
    """
    if not isinstance(text, str):
        return None

    email = try_extract_email(text)
    if email:
        return email

    fixed_text = apply_simple_fixes(text)
    return try_extract_email(fixed_text)


def try_extract_email(text: str) -> str | None:
    """
    Try to extract email from text

    Args:
        text: Text to search for email

    Returns:
        Valid email string or None if no valid email found
    """
    match = EMAIL_REGEX.search(text)
    if match:
        email = match.group(0).lower()
        # Basic validation - must contain @ and end with valid domain
        if "@" in email and (email.endswith(".pl") or email.endswith(".com") or
                             re.search(r"\.[a-z]{2,4}$", email)):
            return email
    return None


def apply_simple_fixes(text: str) -> str:
    """
    Strip off any junk after known valid TLDs

    Args:
        text: Text containing potentially malformed email

    Returns:
        Text with simple fixes applied
    """
    valid_tlds = ["pl", "com", "eu", "edu.pl", "org.pl", "net.pl", "com.pl"]

    for tld in valid_tlds:
        pattern = rf"(\.{tld})([a-zA-Z0-9_]+)\b"
        text = re.sub(pattern, r"\1", text, flags=re.IGNORECASE)

    text = re.sub(r"^\d+\.", "", text)

    return text
