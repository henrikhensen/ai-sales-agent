from fastapi import APIRouter

from backend.api.v1.schemas import ComponentHealth, HealthResponse
from backend.infrastructure.database.session import check_database_connection
from backend.infrastructure.redis.client import check_redis_connection
from backend.shared.config import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()


async def _probe(check) -> ComponentHealth:
    """Run a connectivity check and map the outcome to a component health."""
    try:
        await check()
        return ComponentHealth(status="up")
    except Exception:
        return ComponentHealth(status="down")


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report service liveness and the reachability of core dependencies."""
    components = {
        "database": await _probe(check_database_connection),
        "redis": await _probe(check_redis_connection),
    }
    overall = "ok" if all(c.status == "up" for c in components.values()) else "degraded"
    return HealthResponse(
        status=overall,
        service=settings.app_name,
        environment=settings.app_env,
        components=components,
    )
