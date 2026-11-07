from datetime import datetime
from typing import Literal
from uuid import UUID

from ninja import Field, Schema
from pydantic import field_validator


Visibility = Literal["restricted", "admin", "analyst", "viewer"]
Status = Literal["queued", "processing", "ready", "failed"]


class DocumentOut(Schema):
    id: UUID
    title: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    page_count: int | None
    visibility: Visibility
    status: Status
    failure_reason: str
    version: int
    embedding_model: str
    created_at: datetime
    updated_at: datetime


class DocumentPageOut(Schema):
    items: list[DocumentOut]
    total: int
    limit: int
    offset: int


class PageQuery(Schema):
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


class UpdateVisibilityIn(Schema):
    visibility: Visibility


class SearchKnowledgeIn(Schema):
    query: str = Field(min_length=2, max_length=1000)
    limit: int = Field(default=5, ge=1, le=5)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value):
        if not value.strip():
            raise ValueError("Query must not be blank.")
        return value.strip()


class CitationOut(Schema):
    chunk_id: UUID
    document_id: UUID
    title: str
    page: int | None
    excerpt: str
    score: float


class SearchKnowledgeOut(Schema):
    evidence: list[CitationOut]
    insufficient_evidence: bool
