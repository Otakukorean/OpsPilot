import uuid

from django.conf import settings
from django.db import models

from apps.accounts.models import Workspace


class AuditEvent(models.Model):
    """Immutable security metadata without request or resource payloads."""

    class Outcome(models.TextChoices):
        ALLOWED = "allowed", "Allowed"
        DENIED = "denied", "Denied"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        null=True,
        blank=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=100)
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    resource_type = models.CharField(max_length=32)
    reason = models.CharField(max_length=64, blank=True)
    request_id = models.CharField(max_length=36)
    duration_ms = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["workspace", "created_at"],
                name="audit_ws_created_idx",
            ),
            models.Index(
                fields=["actor", "created_at"],
                name="audit_actor_created_idx",
            ),
            models.Index(
                fields=["action", "outcome"],
                name="audit_action_outcome_idx",
            ),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.action} — {self.outcome}"
