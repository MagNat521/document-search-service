"""Functional-test fixtures.

These tests run the real FastAPI app against a real PostgreSQL and a real
Elasticsearch (the ones from docker-compose). To stay non-destructive they use
an isolated test database (``<db>_test``) and a dedicated ES index
(``documents_test``), both recreated fresh for every test.
"""

import os

from sqlalchemy.engine import make_url

# --- Isolate DB + index BEFORE importing the application ------------------
_BASE_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://search:search@localhost:5432/search"
)
_url = make_url(_BASE_DB_URL)
_TEST_DB = (_url.database or "search") + "_test"
os.environ["DATABASE_URL"] = _url.set(database=_TEST_DB).render_as_string(
    hide_password=False
)
os.environ.setdefault("ELASTICSEARCH_INDEX", "documents_test")

import asyncpg  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app import search  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import Base, dispose_engine, get_engine  # noqa: E402
from app.main import app  # noqa: E402


async def _ensure_test_database() -> None:
    """Create the isolated test database if it does not exist yet."""
    conn = await asyncpg.connect(
        user=_url.username,
        password=_url.password,
        host=_url.host,
        port=_url.port or 5432,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", _TEST_DB
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{_TEST_DB}"')
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    await _ensure_test_database()

    # Fresh database schema.
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Fresh Elasticsearch index.
    es = search.get_es()
    await es.indices.delete(
        index=get_settings().elasticsearch_index, ignore_unavailable=True
    )
    await search.ensure_index()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client

    await es.indices.delete(
        index=get_settings().elasticsearch_index, ignore_unavailable=True
    )
    await search.close_es()
    await dispose_engine()
