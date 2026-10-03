"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """Create or return the process-wide async engine."""
    global _engine, _session_factory
    if _engine is None:
        cfg = settings or get_settings()
        # NullPool avoids cross-event-loop connection reuse in tests.
        engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
        if cfg.app_env == "development":
            engine_kwargs["poolclass"] = NullPool
        _engine = create_async_engine(cfg.database_url, **engine_kwargs)
        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _engine


def get_session_factory(
    settings: Settings | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Return the async session factory, creating the engine if needed."""
    global _session_factory
    if _session_factory is None:
        get_engine(settings)
    assert _session_factory is not None
    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def check_database_connection(settings: Settings | None = None) -> bool:
    """Return True when the database accepts a simple query."""
    engine = get_engine(settings)
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return True


async def dispose_engine() -> None:
    """Dispose the engine and clear cached factories."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
