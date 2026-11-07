import uuid

from django.conf import settings
from django.db import models

from apps.accounts.models import Workspace
from apps.conversations.models import ChatMessage, ChatThread


class AgentRun(models.Model):
    """Payload-free metadata for one bounded assistant generation."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="agent_runs"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="agent_runs",
    )
    thread = models.ForeignKey(
        ChatThread, on_delete=models.CASCADE, related_name="agent_runs"
    )
    user_message = models.OneToOneField(
        ChatMessage,
        on_delete=models.SET_NULL,
        null=True,
        related_name="requested_agent_run",
    )
    assistant_message = models.OneToOneField(
        ChatMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_agent_run",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    model = models.CharField(max_length=100)
    llm_calls = models.PositiveSmallIntegerField(default=0)
    tool_calls = models.PositiveSmallIntegerField(default=0)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["workspace", "created_at"], name="agent_run_ws_created_idx"
            ),
            models.Index(
                fields=["actor", "created_at"], name="agent_run_actor_created_idx"
            ),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.id} ({self.status})"


class ToolInvocation(models.Model):
    """Allowlisted tool audit metadata; arguments and results are never stored."""

    class Outcome(models.TextChoices):
        ALLOWED = "allowed", "Allowed"
        DENIED = "denied", "Denied"
        NOT_FOUND = "not_found", "Not found"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(
        AgentRun, on_delete=models.CASCADE, related_name="tool_invocations"
    )
    tool_name = models.CharField(max_length=64)
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    reason = models.CharField(max_length=64, blank=True)
    duration_ms = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["run", "created_at"], name="agent_tool_run_created_idx")
        ]
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.tool_name} ({self.outcome})"
