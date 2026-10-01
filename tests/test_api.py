"""Functional tests for the document search service."""

from httpx import AsyncClient

from app import search


def _doc(text: str, created_date: str, rubrics: list[str] | None = None) -> dict:
    return {"text": text, "created_date": created_date, "rubrics": rubrics or []}


async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_create_and_get_document(client: AsyncClient):
    payload = _doc("Уникальный текст про дракона", "2020-01-01T10:00:00", ["R1", "R2"])

    resp = await client.post("/documents", json=payload)
    assert resp.status_code == 201
    created = resp.json()
    assert created["id"] > 0
    assert created["text"] == payload["text"]
    assert created["rubrics"] == ["R1", "R2"]
    assert created["created_date"].startswith("2020-01-01T10:00:00")

    got = await client.get(f"/documents/{created['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == created["id"]


async def test_search_rejects_empty_query(client: AsyncClient):
    resp = await client.get("/documents/search", params={"query": ""})
    assert resp.status_code == 422


async def test_search_returns_matches_ordered_by_date(client: AsyncClient):
    docs = [
        _doc("KEYWORDXYZ старая запись", "2019-01-01T00:00:00"),
        _doc("KEYWORDXYZ новая запись", "2021-01-01T00:00:00"),
        _doc("KEYWORDXYZ средняя запись", "2020-01-01T00:00:00"),
        _doc("совсем другой текст без термина", "2022-01-01T00:00:00"),
    ]
    for doc in docs:
        resp = await client.post("/documents", json=doc)
        assert resp.status_code == 201
    await search.refresh_index()

    resp = await client.get("/documents/search", params={"query": "KEYWORDXYZ"})
    assert resp.status_code == 200
    body = resp.json()

    # Only the three documents that contain the term are returned.
    assert body["count"] == 3
    dates = [item["created_date"] for item in body["results"]]
    assert dates == sorted(dates, reverse=True)  # newest first
    assert body["results"][0]["created_date"].startswith("2021-01-01")

    # Ascending order is also supported.
    resp_asc = await client.get(
        "/documents/search", params={"query": "KEYWORDXYZ", "order": "asc"}
    )
    dates_asc = [item["created_date"] for item in resp_asc.json()["results"]]
    assert dates_asc == sorted(dates_asc)


async def test_search_respects_result_limit(client: AsyncClient, monkeypatch):
    # Shrink the page size so we can assert the limit without many docs.
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "search_result_size", 2)

    for i in range(5):
        resp = await client.post(
            "/documents", json=_doc(f"LIMITTOKEN запись {i}", f"2020-01-0{i + 1}T00:00:00")
        )
        assert resp.status_code == 201
    await search.refresh_index()

    body = (
        await client.get("/documents/search", params={"query": "LIMITTOKEN"})
    ).json()
    assert body["count"] == 2  # capped by search_result_size


async def test_delete_removes_from_db_and_index(client: AsyncClient):
    resp = await client.post(
        "/documents", json=_doc("UNIQUETOKEN123 про поиск", "2020-05-05T05:05:05")
    )
    doc_id = resp.json()["id"]
    await search.refresh_index()

    # Present before deletion.
    found = await client.get("/documents/search", params={"query": "UNIQUETOKEN123"})
    assert any(item["id"] == doc_id for item in found.json()["results"])

    # Delete.
    deleted = await client.delete(f"/documents/{doc_id}")
    assert deleted.status_code == 204
    await search.refresh_index()

    # Gone from the DB.
    assert (await client.get(f"/documents/{doc_id}")).status_code == 404
    # Gone from the index.
    after = await client.get("/documents/search", params={"query": "UNIQUETOKEN123"})
    assert all(item["id"] != doc_id for item in after.json()["results"])


async def test_delete_unknown_returns_404(client: AsyncClient):
    resp = await client.delete("/documents/999999")
    assert resp.status_code == 404
