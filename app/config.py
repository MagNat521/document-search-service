"""Application settings loaded from environment variables (and an optional .env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- PostgreSQL ------------------------------------------------------
    database_url: str = "postgresql+asyncpg://search:search@localhost:5432/search"

    # --- Elasticsearch ---------------------------------------------------
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "documents"

    # --- Search behaviour ------------------------------------------------
    # How many documents a single search request returns.
    search_result_size: int = 20
    # How many candidate ids to pull from Elasticsearch (ranked by relevance)
    # before re-ordering them by ``created_date`` in the database. The index
    # only stores ``id`` and ``text`` (per the task spec), so the date ordering
    # has to happen in the DB over this candidate pool.
    search_candidate_pool: int = 1000

    # --- Service metadata ------------------------------------------------
    app_title: str = "Document Search Service"
    app_version: str = "1.0.0"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
