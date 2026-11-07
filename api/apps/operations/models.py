import uuid

from django.db import models

from apps.accounts.models import Workspace


class Transaction(models.Model):
    """Entirely synthetic, read-only transaction data."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    code = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=Status.choices)
    public_detail = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "code"],
                name="operations_transaction_workspace_code_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["workspace", "status"],
                name="ops_tx_ws_status_idx",
            ),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class Ticket(models.Model):
    """Entirely synthetic, read-only support ticket data."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    code = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=Status.choices)
    public_detail = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "code"],
                name="operations_ticket_workspace_code_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["workspace", "status"],
                name="ops_tkt_ws_status_idx",
            ),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code
