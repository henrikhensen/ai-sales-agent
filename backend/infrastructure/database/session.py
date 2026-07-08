from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.shared.config import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped session.

    Acts as a unit of work: the transaction is committed when the request
    handler returns successfully and rolled back if it raises.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def independent_session() -> AsyncGenerator[AsyncSession, None]:
    """A session deliberately independent of any ambient request session.

    Checks out its own connection from the same pool and commits (or rolls
    back on its own exception) on its own schedule — unrelated to whatever
    the caller's enclosing ``get_session`` unit of work does afterward.

    Use this for security-relevant writes that must durably persist even
    when the action they describe is itself rejected — e.g. recording that
    an unsafe admin control change or a blocked dispatch confirmation was
    attempted, immediately before the caller raises a domain exception that
    would otherwise roll back everything written via the ambient session
    (see ``get_session`` below). Never use it for ordinary business data,
    which must keep rolling back atomically with the rest of the request.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database_connection() -> bool:
    """Verify that the database is reachable. Returns True on success."""
    from sqlalchemy import text

    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return True


async def init_database() -> None:
    """Create all tables that do not yet exist.

    Registers the ORM models via import, then issues ``CREATE TABLE IF NOT
    EXISTS`` for the full metadata. Schema migrations are handled by Alembic
    in a later phase.
    """
    import backend.infrastructure.database.models  # noqa: F401  (register metadata)
    from backend.infrastructure.database.base import Base

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Dispose the engine and close all pooled connections."""
    await engine.dispose()
