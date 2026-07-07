import logging

from fastapi import APIRouter, Response

from backend.api.v1.schemas import ComponentHealth, HealthResponse
from backend.infrastructure.database.session import check_database_connection
from backend.infrastructure.redis.client import check_redis_connection
from backend.shared.config import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()
logger = logging.getLogger("backend.health")


async def _probe(name: str, check) -> ComponentHealth:
    """Run a connectivity check and map the outcome to a component health.

    Only logs on failure — health checks are typically polled frequently
    (load balancers, uptime monitors), so logging every successful probe at
    INFO would drown out other application logs.
    """
    try:
        await check()
        return ComponentHealth(status="up")
    except Exception:
        logger.warning("health probe failed: component=%s", name)
        return ComponentHealth(status="down")


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report service liveness and the reachability of core dependencies."""
    components = {
        "database": await _probe("database", check_database_connection),
        "redis": await _probe("redis", check_redis_connection),
    }
    overall = "ok" if all(c.status == "up" for c in components.values()) else "degraded"
    return HealthResponse(
        status=overall,
        service=settings.app_name,
        environment=settings.app_env,
        components=components,
    )


@router.get("/ready", response_model=HealthResponse)
async def ready(response: Response) -> HealthResponse:
    """Report readiness: database and Redis must both be reachable.

    Returns HTTP 503 (with the same body shape) when not ready, so
    orchestrators and load balancers correctly stop routing traffic here —
    unlike ``/health`` above, which always returns 200 to report liveness.
    """
    components = {
        "database": await _probe("database", check_database_connection),
        "redis": await _probe("redis", check_redis_connection),
    }
    overall = "ok" if all(c.status == "up" for c in components.values()) else "degraded"
    if overall != "ok":
        response.status_code = 503
    return HealthResponse(
        status=overall,
        service=settings.app_name,
        environment=settings.app_env,
        components=components,
    )
