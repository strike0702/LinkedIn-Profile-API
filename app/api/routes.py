import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings
from app.models.profile import ProfileResponse
from app.models.requests import ProfileRequest
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api", tags=["profile"])


def get_profile_service() -> ProfileService:
    return ProfileService()


@router.get("/profile", response_model=ProfileResponse)
@limiter.limit(get_settings().rate_limit)
async def get_profile_by_query(
    request: Request,
    url: Annotated[
        str,
        Query(min_length=1, max_length=2048, description="LinkedIn profile URL or slug"),
    ],
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    return await service.get_profile(url)


@router.post("/profile", response_model=ProfileResponse)
@limiter.limit(get_settings().rate_limit)
async def get_profile_by_body(
    request: Request,
    body: ProfileRequest,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    return await service.get_profile(body.url)
