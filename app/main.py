"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import search
from app.config import get_settings
from app.db import dispose_engine, init_models
from app.routers import documents

DESCRIPTION = """
A simple full-text search service over document texts.

* **Storage**: PostgreSQL holds the documents (`id`, `rubrics`, `text`, `created_date`).
* **Index**: Elasticsearch holds `id` + `text` and powers the search.

The service can search documents by text (returning the 20 newest matches with
all DB fields) and delete a document from both stores by `id`.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Wait for dependencies, create the DB schema and the ES index.
    await init_models()
    await search.ensure_index()
    yield
    await search.close_es()
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        description=DESCRIPTION,
        lifespan=lifespan,
    )
    app.include_router(documents.router)

    @app.get("/health", tags=["health"], summary="Health check")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
