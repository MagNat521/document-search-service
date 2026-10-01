"""HTTP endpoints for documents."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import service
from app.db import get_session
from app.schemas import DocumentCreate, DocumentOut, SearchResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Full-text search",
    description=(
        "Searches document text in the Elasticsearch index and returns the first "
        "20 documents (all DB fields) ordered by creation date."
    ),
)
async def search_documents(
    query: str = Query(
        ..., min_length=1, description="Free-text query matched against document text"
    ),
    order: Literal["desc", "asc"] = Query(
        "desc", description="Ordering by created_date: desc (newest first) or asc"
    ),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    results = await service.search_documents(session, query, order)
    return SearchResponse(
        query=query,
        count=len(results),
        results=[DocumentOut.model_validate(doc) for doc in results],
    )


@router.post(
    "",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a document",
    description="Stores a document in the DB and indexes its text in Elasticsearch.",
)
async def create_document(
    payload: DocumentCreate,
    session: AsyncSession = Depends(get_session),
) -> DocumentOut:
    doc = await service.create_document(session, payload)
    return DocumentOut.model_validate(doc)


@router.get(
    "/{doc_id}",
    response_model=DocumentOut,
    summary="Get a document by id",
)
async def get_document(
    doc_id: int,
    session: AsyncSession = Depends(get_session),
) -> DocumentOut:
    doc = await service.get_document(session, doc_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentOut.model_validate(doc)


@router.delete(
    "/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description="Removes a document from both the DB and the search index by id.",
)
async def delete_document(
    doc_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    deleted = await service.delete_document(session, doc_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return None
