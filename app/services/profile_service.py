from app.config import Settings, get_settings
from app.core.url_normalizer import extract_vanity_slug
from app.core.voyager_client import VoyagerClient
from app.models.profile import ProfileResponse
from app.parsers.profile_parser import parse_profile_response
from app.services.cache import InMemoryTTLCache

_profile_cache: InMemoryTTLCache[ProfileResponse] = InMemoryTTLCache()


class ProfileService:
    def __init__(
        self,
        voyager: VoyagerClient | None = None,
        settings: Settings | None = None,
        cache: InMemoryTTLCache[ProfileResponse] | None = None,
    ):
        self.settings = settings or get_settings()
        self.voyager = voyager or VoyagerClient(self.settings)
        self.cache = cache if cache is not None else _profile_cache

    async def get_profile(self, url_or_slug: str) -> ProfileResponse:
        slug = extract_vanity_slug(url_or_slug)

        cached = self.cache.get(slug)
        if cached is not None:
            return cached

        raw = await self.voyager.fetch_profile_raw(slug)
        parsed = parse_profile_response(raw)
        profile = ProfileResponse.model_validate(parsed)

        self.cache.set(slug, profile, self.settings.cache_ttl_seconds)
        return profile

    async def close(self) -> None:
        await self.voyager.close()
