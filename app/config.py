from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    li_at: str = Field(..., alias="LI_AT")
    jsessionid: str = Field(..., alias="JSESSIONID")
    user_agent: str = Field(..., alias="USER_AGENT")

    cache_ttl_seconds: int = Field(default=3600, alias="CACHE_TTL_SECONDS")
    rate_limit: str = Field(default="30/minute", alias="RATE_LIMIT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    voyager_base_url: str = "https://www.linkedin.com"
    decoration_id: str = (
        "com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-91"
    )
    skills_decoration_id: str = (
        "com.linkedin.voyager.dash.deco.identity.profile.FullProfileSkill-28"
    )
    skills_page_size: int = 50
    skills_max_pages: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
