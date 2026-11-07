import logging

from celery import shared_task
from django.db import transaction

from .chunking import chunk_pages
from .embeddings import EmbeddingProviderError, get_embedding_provider
from .extraction import ExtractionError, extract_pages
from .models import Document, DocumentChunk


logger = logging.getLogger("opspilot.knowledge")


def _mark_failed(document_id, reason):
    Document.objects.filter(id=document_id).update(
        status=Document.Status.FAILED,
        failure_reason=reason,
    )


@shared_task(bind=True, max_retries=3)
def ingest_document(self, document_id):
    """Idempotently extract, chunk, embed, and replace one document version."""

    document = Document.objects.filter(id=document_id).first()
    if document is None or document.status == Document.Status.READY:
        return

    Document.objects.filter(id=document_id).update(
        status=Document.Status.PROCESSING,
        failure_reason="",
    )
    try:
        with document.source_file.open("rb") as source:
            data = source.read()
        pages = extract_pages(data, document.content_type)
        chunks = chunk_pages(pages)
        if not chunks:
            raise ExtractionError("no_extractable_text")
        provider = get_embedding_provider()
        vectors = provider.embed([chunk.text for chunk in chunks])
    except EmbeddingProviderError as exc:
        if self.request.retries >= self.max_retries:
            _mark_failed(document_id, "embedding_provider_unavailable")
            logger.error(
                "Document ingestion failed",
                extra={
                    "event": "knowledge.ingestion.failed",
                    "document_id": str(document_id),
                    "reason": "embedding_provider_unavailable",
                },
            )
            return
        raise self.retry(exc=exc, countdown=2 ** (self.request.retries + 1))
    except ExtractionError as exc:
        _mark_failed(document_id, str(exc))
        logger.warning(
            "Document ingestion failed",
            extra={
                "event": "knowledge.ingestion.failed",
                "document_id": str(document_id),
                "reason": str(exc),
            },
        )
        return
    except Exception:
        _mark_failed(document_id, "processing_failed")
        logger.exception(
            "Document ingestion failed",
            extra={
                "event": "knowledge.ingestion.failed",
                "document_id": str(document_id),
                "reason": "processing_failed",
            },
        )
        return

    with transaction.atomic():
        locked = Document.objects.select_for_update().filter(id=document_id).first()
        if locked is None:
            return
        locked.chunks.all().delete()
        DocumentChunk.objects.bulk_create(
            [
                DocumentChunk(
                    document=locked,
                    workspace_id=locked.workspace_id,
                    document_version=locked.version,
                    page=chunk.page,
                    chunk_index=index,
                    text=chunk.text,
                    embedding=vector,
                )
                for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
            ]
        )
        locked.status = Document.Status.READY
        locked.failure_reason = ""
        locked.embedding_model = provider.name
        locked.save(
            update_fields=["status", "failure_reason", "embedding_model", "updated_at"]
        )

    logger.info(
        "Document ingestion completed",
        extra={
            "event": "knowledge.ingestion.ready",
            "document_id": str(document_id),
            "workspace_id": str(document.workspace_id),
            "chunk_count": len(chunks),
        },
    )
