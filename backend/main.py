import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.v1.router import api_router
from backend.infrastructure.database.session import (
    check_database_connection,
    dispose_engine,
    init_database,
)
from backend.infrastructure.redis.client import check_redis_connection, close_redis
from backend.shared.config import get_settings
from backend.shared.logging import configure_logging
from backend.shared.metrics import record_request
from backend.shared.production_checks import get_production_warnings
from backend.shared.security import InvalidTokenError, decode_access_token

settings = get_settings()
configure_logging(settings)
logger = logging.getLogger("backend")

for warning in get_production_warnings(settings):
    logger.warning(warning)


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


def _user_id_from_request(request: Request) -> str:
    """Best-effort user id for a log line, decoded from the bearer JWT.

    Never logs the token itself — only the ``sub`` claim, and only if the
    token is present and valid. Returns "anonymous" otherwise.
    """
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        return "anonymous"
    try:
        payload = decode_access_token(authorization[len("Bearer ") :])
        return str(payload.get("sub", "anonymous"))
    except InvalidTokenError:
        return "anonymous"


request_logger = logging.getLogger("backend.requests")


@app.middleware("http")
async def add_request_logging(request: Request, call_next):
    """Record request metrics and, if enabled, log one structured line per
    request: id, method, path, status, duration, and user id (from the
    JWT, never the token itself).

    Metrics are always recorded (cheap in-memory counters); only the log
    line itself is gated by ENABLE_REQUEST_LOGGING. Never logs
    request/response bodies, headers, query strings, passwords, tokens, or
    API keys — see backend/shared/logging.py's redaction filter as a
    defense-in-depth backstop for anything that slips through anyway.
    """
    request_id = str(uuid.uuid4())
    started_at = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started_at) * 1000

    record_request(response.status_code, duration_ms)

    if settings.enable_request_logging:
        request_logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.1f user_id=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            _user_id_from_request(request),
        )
    response.headers.setdefault("X-Request-ID", request_id)
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


@app.get("/health", tags=["root"])
async def root_health() -> dict[str, str]:
    """Unprefixed liveness alias for hosts/orchestrators that probe a
    conventional ``/health`` path. Equivalent to ``GET /api/v1/health`` but
    without the dependency checks — use the ``/api/v1`` endpoints for a
    full readiness picture."""
    return {"status": "ok"}


@app.get("/ready", tags=["root"])
async def root_ready(response: Response) -> dict[str, object]:
    """Unprefixed readiness alias: checks the database and Redis are
    reachable. Returns HTTP 503 if either is down, so orchestrators (k8s,
    most PaaS health checks) correctly stop routing traffic here."""
    database_up = await _safe_check(check_database_connection)
    redis_up = await _safe_check(check_redis_connection)
    ready = database_up and redis_up
    response.status_code = 200 if ready else 503
    return {
        "status": "ready" if ready else "not_ready",
        "database": "up" if database_up else "down",
        "redis": "up" if redis_up else "down",
    }


async def _safe_check(check) -> bool:
    try:
        await check()
        return True
    except Exception:
        return False
