import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from pgvector.django import VectorField

from apps.accounts.models import Workspace


def private_document_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"knowledge/{instance.workspace_id}/{instance.id}/source{extension}"


class Document(models.Model):
    """Private, workspace-scoped source document and ingestion state."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    class Visibility(models.TextChoices):
        RESTRICTED = "restricted", "Restricted (unpublished)"
        ADMIN = "admin", "Admins"
        ANALYST = "analyst", "Admins and analysts"
        VIEWER = "viewer", "All workspace roles"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="uploaded_documents",
        null=True,
    )
    title = models.CharField(max_length=255)
    source_file = models.FileField(upload_to=private_document_path, max_length=500)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.RESTRICTED,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    failure_reason = models.CharField(max_length=64, blank=True)
    version = models.PositiveIntegerField(default=1)
    embedding_model = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "status"], name="knowledge_doc_ws_status_idx"),
            models.Index(
                fields=["workspace", "visibility"],
                name="knowledge_doc_ws_vis_idx",
            ),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.title


class DocumentChunk(models.Model):
    """Extracted untrusted text and its vector representation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="document_chunks",
    )
    document_version = models.PositiveIntegerField()
    page = models.PositiveIntegerField(null=True, blank=True)
    chunk_index = models.PositiveIntegerField()
    text = models.TextField()
    embedding = VectorField(dimensions=384)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "document_version", "chunk_index"],
                name="knowledge_chunk_doc_version_index_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["workspace", "document"],
                name="knowledge_chunk_ws_doc_idx",
            ),
        ]
        ordering = ["document_id", "chunk_index"]

    def __str__(self):
        return f"{self.document.title} #{self.chunk_index}"
