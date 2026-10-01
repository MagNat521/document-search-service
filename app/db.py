"""Async SQLAlchemy engine, session factory and schema bootstrap."""

import asyncio
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a request-scoped session."""
    async with get_sessionmaker()() as session:
        yield session


async def init_models(retries: int = 30, delay: float = 2.0) -> None:
    """Create tables if they do not exist, waiting for the database to come up.

    ``create_all`` is used instead of migrations to keep this test service
    easy to run; a production service would use Alembic.
    """
    # Import models so they are registered on ``Base.metadata`` before create_all.
    from app import models  # noqa: F401

    last_error: Exception | None = None
    for _ in range(retries):
        try:
            async with get_engine().begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return
        except Exception as exc:  # pragma: no cover - startup resilience
            last_error = exc
            await asyncio.sleep(delay)
    raise RuntimeError(f"Database is not reachable: {last_error}")


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
