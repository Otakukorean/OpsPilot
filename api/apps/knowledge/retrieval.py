import re
from dataclasses import dataclass

from django.conf import settings
from pgvector.django import CosineDistance

from .embeddings import get_embedding_provider
from .models import Document, DocumentChunk
from .permissions import permitted_visibilities


TITLE_SEPARATOR_RE = re.compile(r"[\W_]+", re.UNICODE)


@dataclass(frozen=True)
class Evidence:
    chunk_id: object
    document_id: object
    title: str
    page: int | None
    excerpt: str
    score: float


def _normalize_title(value):
    """Normalize filename-style titles without weakening authorization."""

    return TITLE_SEPARATOR_RE.sub(" ", value.casefold()).strip()


def _title_matched_document_ids(*, documents, query):
    normalized_query = f" {_normalize_title(query)} "
    matches = []
    for document_id, title in documents.values_list("id", "title"):
        normalized_title = _normalize_title(title)
        if len(normalized_title) >= 2 and f" {normalized_title} " in normalized_query:
            matches.append((document_id, normalized_title))

    # If titles overlap, prefer the most specific title while still supporting
    # questions that explicitly name multiple distinct documents.
    return {
        document_id
        for document_id, title in matches
        if not any(
            title != other_title and f" {title} " in f" {other_title} "
            for _, other_title in matches
        )
    }


def search_authorized_knowledge(*, membership, query, limit=5):
    """Search only SQL-authorized chunks and return citation-ready evidence."""

    provider = get_embedding_provider()
    query_vector = provider.embed([query])[0]
    if not any(query_vector):
        return []

    authorized_documents = Document.objects.filter(
        workspace_id=membership.workspace_id,
        status=Document.Status.READY,
        visibility__in=permitted_visibilities(membership.role),
        embedding_model=provider.name,
    )
    allowed = DocumentChunk.objects.filter(
        workspace_id=membership.workspace_id,
        document__in=authorized_documents,
    ).select_related("document")
    ranked = allowed.annotate(distance=CosineDistance("embedding", query_vector))
    title_document_ids = _title_matched_document_ids(
        documents=authorized_documents,
        query=query,
    )
    if title_document_ids:
        rows = list(
            ranked.filter(document_id__in=title_document_ids)
            .order_by("document_id", "chunk_index", "id")[:limit]
        )
    else:
        max_distance = 1.0 - settings.KNOWLEDGE_MIN_SIMILARITY
        rows = list(
            ranked.filter(distance__lte=max_distance)
            .order_by("distance", "id")[:limit]
        )
    return [
        Evidence(
            chunk_id=row.id,
            document_id=row.document_id,
            title=row.document.title,
            page=row.page,
            excerpt=row.text[:300],
            score=round(1.0 - float(row.distance), 6),
        )
        for row in rows
    ]
