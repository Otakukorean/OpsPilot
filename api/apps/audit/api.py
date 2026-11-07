import logging

from ninja import Query, Router
from ninja.errors import HttpError

from apps.accounts.models import Membership
from apps.accounts.schemas import ErrorOut, ValidationErrorOut

from .models import AuditEvent
from .schemas import AuditEventPageOut, AuditQuery
from .services import record_audit_event


audit_logger = logging.getLogger("opspilot.audit")
audit_router = Router(tags=["Audit"])


def _resolve_admin_membership(request):
    membership = (
        request.auth.memberships.filter(is_active=True)
        .select_related("workspace")
        .first()
    )
    if membership is None or membership.role != Membership.Role.ADMIN:
        record_audit_event(
            request=request,
            action="audit.list",
            outcome=AuditEvent.Outcome.DENIED,
            resource_type="audit_event",
            reason="admin_role_required",
            workspace_id=membership.workspace_id if membership else None,
        )
        audit_logger.warning(
            "Audit access denied",
            extra={
                "event": "audit.list.denied",
                "request_id": request.request_id,
                "user_id": str(request.auth.pk),
                "workspace_id": (
                    str(membership.workspace_id) if membership else None
                ),
                "role": membership.role if membership else None,
                "outcome": "denied",
                "reason": "admin_role_required",
            },
        )
        raise HttpError(403, "Admin role required.")
    return membership


@audit_router.get(
    "/admin/audit",
    response={
        200: AuditEventPageOut,
        401: ErrorOut,
        403: ErrorOut,
        422: ValidationErrorOut,
    },
    operation_id="listAuditEvents",
    summary="List workspace audit metadata",
    description=(
        "Returns metadata-only audit events for the authenticated Admin's active "
        "workspace. Raw request payloads and resource contents are never stored."
    ),
)
def list_audit_events(request, filters: Query[AuditQuery]):
    membership = _resolve_admin_membership(request)
    queryset = AuditEvent.objects.filter(workspace_id=membership.workspace_id)
    if filters.action is not None:
        queryset = queryset.filter(action=filters.action)
    if filters.outcome is not None:
        queryset = queryset.filter(outcome=filters.outcome)
    if filters.resource_type is not None:
        queryset = queryset.filter(resource_type=filters.resource_type)

    queryset = queryset.order_by("-created_at", "-id")
    total = queryset.count()
    items = list(queryset[filters.offset : filters.offset + filters.limit])
    record_audit_event(
        request=request,
        action="audit.list",
        outcome=AuditEvent.Outcome.ALLOWED,
        resource_type="audit_event",
        workspace_id=membership.workspace_id,
    )
    audit_logger.info(
        "Audit access allowed",
        extra={
            "event": "audit.list.allowed",
            "request_id": request.request_id,
            "user_id": str(request.auth.pk),
            "workspace_id": str(membership.workspace_id),
            "role": membership.role,
            "outcome": "allowed",
            "result_count": len(items),
            "limit": filters.limit,
            "offset": filters.offset,
        },
    )
    return {
        "items": items,
        "total": total,
        "limit": filters.limit,
        "offset": filters.offset,
    }
