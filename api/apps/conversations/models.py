import uuid

from django.conf import settings
from django.db import models

from apps.accounts.models import Workspace


class ChatThread(models.Model):
    """A workspace-scoped conversation owned by one user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="chat_threads",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_threads",
    )
    title = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["workspace", "owner", "updated_at"],
                name="chat_thread_ws_owner_idx",
            ),
        ]
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return self.title


class ChatMessage(models.Model):
    """A persisted chat message; generation is implemented in a later milestone."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    class Status(models.TextChoices):
        STORED = "stored", "Stored"
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(
        ChatThread,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    body = models.TextField(max_length=4_000)
    status = models.CharField(max_length=16, choices=Status.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["thread", "created_at"],
                name="chat_message_thread_idx",
            ),
        ]
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role} message in {self.thread_id}"


class MessageCitation(models.Model):
    """Server-validated knowledge source attached to an assistant message."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        ChatMessage, on_delete=models.CASCADE, related_name="citations"
    )
    document = models.ForeignKey(
        "knowledge.Document", on_delete=models.CASCADE, related_name="message_citations"
    )
    chunk = models.ForeignKey(
        "knowledge.DocumentChunk", on_delete=models.CASCADE, related_name="message_citations"
    )
    source_number = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=255)
    page = models.PositiveIntegerField(null=True, blank=True)
    excerpt = models.CharField(max_length=300)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "source_number"],
                name="conversation_citation_message_source_unique",
            ),
            models.UniqueConstraint(
                fields=["message", "chunk"],
                name="conversation_citation_message_chunk_unique",
            ),
        ]
        ordering = ["source_number"]
