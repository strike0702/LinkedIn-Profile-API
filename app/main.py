import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import limiter, router
from app.config import get_settings
from app.core.errors import (
    ForbiddenError,
    InvalidURLError,
    LinkedInProfileAPIError,
    ProfileNotFoundError,
    RateLimitError,
    UnauthorizedError,
    UpstreamError,
)

logger = logging.getLogger(__name__)


def _error_response(status: int, error: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": error, "detail": detail, "status": status},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    logger.info("LinkedIn Profile API starting")
    yield
    logger.info("LinkedIn Profile API shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="LinkedIn Profile API",
        description="Extract structured LinkedIn profile data via the Voyager API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(InvalidURLError)
    async def invalid_url_handler(_: Request, exc: InvalidURLError) -> JSONResponse:
        return _error_response(400, "invalid_url", exc.detail)

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(_: Request, exc: UnauthorizedError) -> JSONResponse:
        return _error_response(401, "unauthorized", exc.detail)

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(_: Request, exc: ForbiddenError) -> JSONResponse:
        return _error_response(403, "forbidden", exc.detail)

    @app.exception_handler(ProfileNotFoundError)
    async def not_found_handler(_: Request, exc: ProfileNotFoundError) -> JSONResponse:
        return _error_response(404, "not_found", exc.detail)

    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(_: Request, exc: RateLimitError) -> JSONResponse:
        return _error_response(429, "rate_limit_exceeded", exc.detail)

    @app.exception_handler(UpstreamError)
    async def upstream_handler(_: Request, exc: UpstreamError) -> JSONResponse:
        return _error_response(502, "upstream_error", exc.detail)

    @app.exception_handler(LinkedInProfileAPIError)
    async def generic_handler(_: Request, exc: LinkedInProfileAPIError) -> JSONResponse:
        return _error_response(500, "internal_error", exc.detail)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app


app = create_app()
