import pytest

from app.core.errors import InvalidURLError
from app.core.url_normalizer import extract_vanity_slug


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        ("https://www.linkedin.com/in/john-doe/", "john-doe"),
        ("http://linkedin.com/in/john-doe?foo=bar", "john-doe"),
        ("linkedin.com/in/john-doe", "john-doe"),
        ("john-doe", "john-doe"),
        ("John-Doe", "john-doe"),
        ("https://www.linkedin.com/in/jane-smith", "jane-smith"),
    ],
)
def test_extract_vanity_slug_valid(input_value, expected):
    assert extract_vanity_slug(input_value) == expected


@pytest.mark.parametrize(
    "input_value",
    [
        "",
        "   ",
        "https://twitter.com/johndoe",
        "https://example.com/in/john-doe",
        "not-a-valid-slug-",
        "-bad-slug",
        "bad slug with spaces",
    ],
)
def test_extract_vanity_slug_invalid(input_value):
    with pytest.raises(InvalidURLError):
        extract_vanity_slug(input_value)
