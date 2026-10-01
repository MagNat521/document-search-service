"""ORM models."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Document(Base):
    """A searchable document.

    Mirrors the storage structure from the task:
      * id            - unique identifier (generated on ingest);
      * rubrics       - array of rubric codes;
      * text          - document body;
      * created_date  - creation timestamp.
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rubrics: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Indexed because every search result is ordered by this column.
    created_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, index=True
    )
