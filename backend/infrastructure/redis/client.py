from redis.asyncio import Redis, from_url

from backend.shared.config import get_settings

settings = get_settings()

redis_client: Redis = from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> Redis:
    """FastAPI dependency that returns the shared Redis client."""
    return redis_client


async def check_redis_connection() -> bool:
    """Verify that Redis is reachable. Returns True on success."""
    return await redis_client.ping()


async def close_redis() -> None:
    """Close the Redis connection pool."""
    await redis_client.aclose()
