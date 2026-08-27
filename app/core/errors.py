class LinkedInProfileAPIError(Exception):
    """Base exception for API errors."""

    def __init__(self, message: str, detail: str | None = None):
        self.message = message
        self.detail = detail or message
        super().__init__(message)


class InvalidURLError(LinkedInProfileAPIError):
    """Raised when the input URL or slug is invalid."""


class UnauthorizedError(LinkedInProfileAPIError):
    """Raised when LinkedIn session is invalid or expired."""


class ForbiddenError(LinkedInProfileAPIError):
    """Raised when LinkedIn denies access to the profile."""


class ProfileNotFoundError(LinkedInProfileAPIError):
    """Raised when the profile does not exist."""


class RateLimitError(LinkedInProfileAPIError):
    """Raised when LinkedIn or our API rate limit is exceeded."""


class UpstreamError(LinkedInProfileAPIError):
    """Raised when LinkedIn returns an unexpected error."""
