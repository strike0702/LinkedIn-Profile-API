import re

from app.core.errors import InvalidURLError

# LinkedIn vanity slug: letters, digits, hyphens; must start/end with alnum
_SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,98}[a-zA-Z0-9])?$")

# Full URL or path containing /in/{slug}
_LINKEDIN_IN_PATTERN = re.compile(
    r"(?:https?://)?(?:[\w-]+\.)?linkedin\.com/in/([a-zA-Z0-9-]+)",
    re.IGNORECASE,
)


def extract_vanity_slug(url_or_slug: str) -> str:
    """Extract LinkedIn vanity slug from various input forms.

    Accepts:
    - Full URLs: https://www.linkedin.com/in/john-doe/
    - Paths: linkedin.com/in/john-doe
    - Plain slugs: john-doe

    Raises InvalidURLError for malformed or non-LinkedIn inputs.
    """
    if not url_or_slug or not url_or_slug.strip():
        raise InvalidURLError("URL or slug is required")

    value = url_or_slug.strip().rstrip("/")

    # Try LinkedIn URL/path pattern first
    match = _LINKEDIN_IN_PATTERN.search(value)
    if match:
        slug = match.group(1)
        if _SLUG_PATTERN.match(slug):
            return slug.lower()
        raise InvalidURLError(f"Invalid vanity slug in URL: {slug}")

    # Reject URLs that look like other domains
    if "://" in value or value.startswith("www."):
        raise InvalidURLError(f"Not a LinkedIn profile URL: {value}")

    # Reject paths that aren't LinkedIn /in/ paths
    if "/" in value and "linkedin" not in value.lower():
        raise InvalidURLError(f"Not a LinkedIn profile URL: {value}")

    # Treat as plain slug
    if _SLUG_PATTERN.match(value):
        return value.lower()

    raise InvalidURLError(f"Invalid vanity slug: {value}")
