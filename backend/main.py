import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.v1.router import api_router
from backend.infrastructure.database.session import dispose_engine, init_database
from backend.infrastructure.redis.client import close_redis
from backend.shared.config import get_settings
from backend.shared.logging import configure_logging

settings = get_settings()
configure_logging(settings)
logger = logging.getLogger("backend")

if settings.app_env == "production" and "*" in settings.cors_allowed_origins_list:
    logger.warning(
        "CORS_ALLOWED_ORIGINS is '*' while APP_ENV=production; restrict this to "
        "the real frontend origin(s) before going live."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of shared infrastructure resources."""
    logger.info(
        "startup: app=%s env=%s llm_provider=%s",
        settings.app_name,
        settings.app_env,
        settings.llm_provider,
    )
    await init_database()
    yield
    await dispose_engine()
    await close_redis()
    logger.info("shutdown: connections closed")


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Attach a minimal set of defensive security headers to every response."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log the full error server-side but never leak internals to the client.

    FastAPI's default handlers for ``HTTPException`` and validation errors are
    more specific and take precedence, so this only catches genuinely
    unexpected failures.
    """
    logger.exception(
        "unhandled exception on %s %s", request.method, request.url.path
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint returning basic service metadata."""
    return {"service": settings.app_name, "status": "running"}
