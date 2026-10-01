"""Elasticsearch client and index helpers.

The search index deliberately stores only ``id`` and ``text`` (as required by
the task). Date ordering of search results is therefore done in the database.
"""

import asyncio

from elasticsearch import AsyncElasticsearch, NotFoundError

from app.config import get_settings

# Mapping for the index body (passed to ``indices.create(mappings=...)``).
INDEX_MAPPINGS: dict = {
    "properties": {
        "id": {"type": "long"},
        "text": {"type": "text"},
    }
}

_client: AsyncElasticsearch | None = None


def get_es() -> AsyncElasticsearch:
    global _client
    if _client is None:
        _client = AsyncElasticsearch(hosts=[get_settings().elasticsearch_url])
    return _client


async def ensure_index(retries: int = 60, delay: float = 2.0) -> None:
    """Create the index if missing, waiting for Elasticsearch to come up."""
    es = get_es()
    index = get_settings().elasticsearch_index
    last_error: Exception | None = None
    for _ in range(retries):
        try:
            if not await es.indices.exists(index=index):
                await es.indices.create(index=index, mappings=INDEX_MAPPINGS)
            return
        except Exception as exc:  # pragma: no cover - startup resilience
            last_error = exc
            await asyncio.sleep(delay)
    raise RuntimeError(f"Elasticsearch is not reachable: {last_error}")


async def index_document(doc_id: int, text: str) -> None:
    """Add or replace a document in the index."""
    es = get_es()
    await es.index(
        index=get_settings().elasticsearch_index,
        id=str(doc_id),
        document={"id": doc_id, "text": text},
    )


async def delete_from_index(doc_id: int) -> None:
    """Remove a document from the index; ignore if it is already gone."""
    es = get_es()
    try:
        await es.delete(index=get_settings().elasticsearch_index, id=str(doc_id))
    except NotFoundError:
        pass


async def search_ids(query: str, size: int) -> list[int]:
    """Return ids of documents whose ``text`` matches ``query`` (by relevance)."""
    es = get_es()
    response = await es.search(
        index=get_settings().elasticsearch_index,
        query={"match": {"text": query}},
        size=size,
        source=False,
    )
    return [int(hit["_id"]) for hit in response["hits"]["hits"]]


async def refresh_index() -> None:
    """Force a refresh so just-indexed documents become searchable immediately.

    Elasticsearch is near-real-time; writes are visible to search only after a
    refresh (~1s by default). Useful for tests and bulk ingest.
    """
    es = get_es()
    await es.indices.refresh(index=get_settings().elasticsearch_index)


async def close_es() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
