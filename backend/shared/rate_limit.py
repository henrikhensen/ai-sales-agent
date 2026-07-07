"""Rate limiting: memory or Redis-backed fixed-window counters.

Applied per authenticated caller (the JWT ``sub`` claim, decoded without a
database lookup) or per hashed IP otherwise — a raw IP is never stored or
logged, only a short one-way hash used as an in-memory/Redis key. Gated by
``RATE_LIMIT_ENABLED``; when disabled, every check passes through
immediately. If ``RATE_LIMIT_BACKEND=redis`` but Redis is unreachable, this
falls back to the in-memory counter for that request rather than ever
failing the request or crashing.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from backend.shared.config import Settings, get_settings
from backend.shared.security import InvalidTokenError, decode_access_token

logger = logging.getLogger("backend.rate_limit")

# In-process fallback store: key -> (window_start_epoch_seconds, count).
# Fine for a single instance; RATE_LIMIT_BACKEND=redis is required for
# correct shared limits across multiple backend instances.
_memory_store: dict[str, tuple[float, int]] = {}


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int


def hash_identity(value: str) -> str:
    """One-way hash used for the rate-limit key — never store the raw IP."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def client_identity(request: Request) -> str:
    """Best-effort caller identity: the JWT subject if present and valid,
    else a hashed client IP. Never returns or stores a raw IP beyond this
    hash."""
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        try:
            payload = decode_access_token(authorization[len("Bearer ") :])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except InvalidTokenError:
            pass
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{hash_identity(client_host)}"


def _check_memory(key: str, limit: int, window_seconds: int) -> RateLimitResult:
    now = time.time()
    window_start, count = _memory_store.get(key, (now, 0))
    if now - window_start >= window_seconds:
        window_start, count = now, 0
    count += 1
    _memory_store[key] = (window_start, count)
    if count > limit:
        retry_after = max(1, int(window_seconds - (now - window_start)))
        return RateLimitResult(allowed=False, retry_after_seconds=retry_after)
    return RateLimitResult(allowed=True, retry_after_seconds=0)


async def _check_redis(key: str, limit: int, window_seconds: int) -> RateLimitResult:
    from backend.infrastructure.redis.client import redis_client

    full_key = f"ratelimit:{key}"
    count = await redis_client.incr(full_key)
    if count == 1:
        await redis_client.expire(full_key, window_seconds)
    if count > limit:
        ttl = await redis_client.ttl(full_key)
        retry_after = ttl if ttl and ttl > 0 else window_seconds
        return RateLimitResult(allowed=False, retry_after_seconds=retry_after)
    return RateLimitResult(allowed=True, retry_after_seconds=0)


async def check_rate_limit(
    key: str, limit: int, window_seconds: int, settings: Settings
) -> RateLimitResult:
    if settings.rate_limit_backend == "redis":
        try:
            return await _check_redis(key, limit, window_seconds)
        except Exception:
            logger.warning(
                "Redis unreachable for rate limiting; falling back to the "
                "in-memory counter for this request."
            )
            return _check_memory(key, limit, window_seconds)
    return _check_memory(key, limit, window_seconds)


def reset_memory_store() -> None:
    """Test-only: clear the in-memory counters between test cases."""
    _memory_store.clear()


def rate_limit(scope: str, limit_attr: str, window_seconds: int):
    """FastAPI dependency factory enforcing a named rate-limit scope.

    ``limit_attr`` is the ``Settings`` attribute holding the per-scope
    limit (e.g. ``"rate_limit_auth_per_minute"``), so limits stay
    centrally configurable in one place (``backend/shared/config.py``)
    without touching call sites. Raises HTTP 429 with a ``Retry-After``
    header when the limit is exceeded — never blocks silently, never
    crashes the request for any other reason.
    """

    async def _dependency(request: Request) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return
        limit = getattr(settings, limit_attr)
        identity = client_identity(request)
        key = f"{scope}:{identity}"
        result = await check_rate_limit(key, limit, window_seconds, settings)
        if not result.allowed:
            request.state.rate_limit_scope = scope
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded for '{scope}'. Try again in "
                    f"{result.retry_after_seconds} second(s)."
                ),
                headers={"Retry-After": str(result.retry_after_seconds)},
            )

    return _dependency
