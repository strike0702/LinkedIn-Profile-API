import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.config import Settings, get_settings
from app.core.errors import (
    ForbiddenError,
    ProfileNotFoundError,
    RateLimitError,
    UnauthorizedError,
    UpstreamError,
)

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {500, 502, 503, 504}


class VoyagerClient:
    """Async HTTP client for LinkedIn Voyager profile API."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client: httpx.AsyncClient | None = None

    def _build_headers(self) -> dict[str, str]:
        jsessionid = self.settings.jsessionid.strip('"')
        return {
            "Cookie": f'li_at={self.settings.li_at}; JSESSIONID="{jsessionid}"',
            "csrf-token": jsessionid,
            "x-restli-protocol-version": "2.0.0",
            "Accept": "application/vnd.linkedin.normalized+json+2.1",
            "User-Agent": self.settings.user_agent,
            "x-li-lang": "en_US",
        }

    def _profile_url(self, slug: str) -> str:
        decoration = self.settings.decoration_id
        return (
            f"{self.settings.voyager_base_url}/voyager/api/identity/dash/profiles"
            f"?q=memberIdentity&memberIdentity={slug}"
            f"&decorationId={decoration}"
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                http2=True,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _map_status_error(self, status: int, slug: str) -> None:
        if status == 401:
            raise UnauthorizedError(
                "LinkedIn session expired or invalid",
                "Check LI_AT and JSESSIONID environment variables",
            )
        if status == 403:
            raise ForbiddenError(
                "Access denied by LinkedIn",
                f"LinkedIn denied access to profile '{slug}'",
            )
        if status == 404:
            raise ProfileNotFoundError(
                "Profile not found",
                f"No LinkedIn profile found for slug '{slug}'",
            )
        if status == 429:
            raise RateLimitError(
                "Rate limit exceeded",
                "LinkedIn rate limit reached; try again later",
            )
        if status >= 500:
            raise UpstreamError(
                "LinkedIn service error",
                f"LinkedIn returned HTTP {status}",
            )
        raise UpstreamError(
            "Unexpected upstream response",
            f"LinkedIn returned HTTP {status} for profile '{slug}'",
        )

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, UpstreamError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        reraise=True,
    )
    async def fetch_profile_raw(self, slug: str) -> dict[str, Any]:
        """Fetch raw Voyager profile JSON for a vanity slug."""
        client = await self._get_client()
        url = self._profile_url(slug)
        headers = self._build_headers()

        logger.info("Fetching LinkedIn profile", extra={"slug": slug})

        try:
            response = await client.get(url, headers=headers)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            logger.warning(
                "Network error fetching profile",
                extra={"slug": slug, "error": str(exc)},
            )
            raise UpstreamError("Network error contacting LinkedIn", str(exc)) from exc

        if response.status_code == 200:
            return response.json()

        if response.status_code == 429:
            self._map_status_error(429, slug)

        if response.status_code in RETRYABLE_STATUS:
            raise UpstreamError(
                "Retryable upstream error",
                f"LinkedIn returned HTTP {response.status_code}",
            )

        self._map_status_error(response.status_code, slug)
        return {}  # unreachable
