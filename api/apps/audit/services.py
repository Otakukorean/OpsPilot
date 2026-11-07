import time

from .models import AuditEvent


def record_audit_event(
    *,
    request,
    action,
    outcome,
    resource_type,
    reason="",
    workspace_id=None,
):
    """Persist allowlisted audit metadata; payload fields are intentionally absent."""

    actor = getattr(request, "user", None)
    if actor is None or not actor.is_authenticated:
        actor = None

    if workspace_id is None and actor is not None:
        workspace_id = (
            actor.memberships.filter(is_active=True)
            .values_list("workspace_id", flat=True)
            .first()
        )

    started_at = getattr(request, "request_started_at", None)
    duration_ms = None
    if started_at is not None:
        duration_ms = round((time.monotonic() - started_at) * 1000, 2)

    return AuditEvent.objects.create(
        workspace_id=workspace_id,
        actor=actor,
        action=action,
        outcome=outcome,
        resource_type=resource_type,
        reason=reason,
        request_id=getattr(request, "request_id", "unavailable"),
        duration_ms=duration_ms,
    )
