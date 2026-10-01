"""Pydantic request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentBase(BaseModel):
    text: str = Field(..., description="Full text of the document")
    rubrics: list[str] = Field(
        default_factory=list, description="List of rubric codes the document belongs to"
    )
    created_date: datetime = Field(..., description="Document creation timestamp")


class DocumentCreate(DocumentBase):
    """Payload for creating a document."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "Пример текста документа про Brawl Stars",
                "rubrics": ["VK-1603736028819866", "VK-11879320040"],
                "created_date": "2019-07-25T12:42:13",
            }
        }
    )


class DocumentOut(DocumentBase):
    """A document as returned by the API (all DB fields)."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique document identifier")


class SearchResponse(BaseModel):
    """Search results: up to ``search_result_size`` documents, newest first."""

    query: str = Field(..., description="The query that was executed")
    count: int = Field(..., description="Number of documents returned")
    results: list[DocumentOut] = Field(
        default_factory=list, description="Matching documents ordered by created_date"
    )
