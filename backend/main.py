from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.v1.router import api_router
from backend.infrastructure.database.session import dispose_engine, init_database
from backend.infrastructure.redis.client import close_redis
from backend.shared.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of shared infrastructure resources."""
    await init_database()
    yield
    await dispose_engine()
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint returning basic service metadata."""
    return {"service": settings.app_name, "status": "running"}
