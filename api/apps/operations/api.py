import logging
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from ninja import Query, Router
from ninja.errors import HttpError

from apps.accounts.schemas import ErrorOut
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event

from .models import Ticket, Transaction
from .permissions import resolve_operations_membership
from .schemas import (
    TicketOut,
    TicketPageOut,
    TicketQuery,
    TransactionOut,
    TransactionPageOut,
    TransactionQuery,
)


audit_logger = logging.getLogger("opspilot.operations")
operations_router = Router(tags=["Operations"])


def _resolve_membership(request, resource_type, action):
    try:
        return resolve_operations_membership(request.auth)
    except PermissionDenied:
        record_audit_event(
            request=request,
            action=f"operations.{resource_type}.{action}",
            outcome=AuditEvent.Outcome.DENIED,
            resource_type=resource_type,
            reason="role_not_allowed_or_membership_inactive",
        )
        audit_logger.warning(
            "Operations read denied",
            extra={
                "event": f"operations.{resource_type}.{action}.denied",
                "request_id": request.request_id,
                "user_id": str(request.auth.pk),
                "outcome": "denied",
                "reason": "role_not_allowed_or_membership_inactive",
            },
        )
        raise HttpError(403, "Operations access denied.") from None


def _get_scoped_record(request, model, object_id):
    resource_type = model._meta.model_name
    membership = _resolve_membership(request, resource_type, "read")
    record = model.objects.filter(
        id=object_id,
        workspace_id=membership.workspace_id,
    ).first()
    if record is None:
        record_audit_event(
            request=request,
            action=f"operations.{resource_type}.read",
            outcome=AuditEvent.Outcome.DENIED,
            resource_type=resource_type,
            reason="not_found_in_workspace",
            workspace_id=membership.workspace_id,
        )
        audit_logger.warning(
            "Scoped operations record not found",
            extra={
                "event": f"operations.{resource_type}.read.not_found",
                "request_id": request.request_id,
                "user_id": str(request.auth.pk),
                "workspace_id": str(membership.workspace_id),
                "role": membership.role,
                "outcome": "denied",
                "reason": "not_found_in_workspace",
            },
        )
        raise HttpError(404, "Resource not found.")

    record_audit_event(
        request=request,
        action=f"operations.{resource_type}.read",
        outcome=AuditEvent.Outcome.ALLOWED,
        resource_type=resource_type,
        workspace_id=membership.workspace_id,
    )
    audit_logger.info(
        "Scoped operations read allowed",
        extra={
            "event": f"operations.{resource_type}.read.allowed",
            "request_id": request.request_id,
            "user_id": str(request.auth.pk),
            "workspace_id": str(membership.workspace_id),
            "role": membership.role,
            "outcome": "allowed",
        },
    )
    return record


def _page(queryset, filters):
    total = queryset.count()
    items = list(queryset[filters.offset : filters.offset + filters.limit])
    return {
        "items": items,
        "total": total,
        "limit": filters.limit,
        "offset": filters.offset,
    }


def _log_query_allowed(request, membership, resource_type, page):
    record_audit_event(
        request=request,
        action=f"operations.{resource_type}.query",
        outcome=AuditEvent.Outcome.ALLOWED,
        resource_type=resource_type,
        workspace_id=membership.workspace_id,
    )
    audit_logger.info(
        "Scoped operations query allowed",
        extra={
            "event": f"operations.{resource_type}.query.allowed",
            "request_id": request.request_id,
            "user_id": str(request.auth.pk),
            "workspace_id": str(membership.workspace_id),
            "role": membership.role,
            "outcome": "allowed",
            "result_count": len(page["items"]),
            "limit": page["limit"],
            "offset": page["offset"],
        },
    )


@operations_router.get(
    "/transactions",
    response={
        200: TransactionPageOut,
        401: ErrorOut,
        403: ErrorOut,
    },
    operation_id="queryTransactions",
    summary="Query synthetic transactions",
    description=(
        "Returns a bounded page of fictional transactions for an Admin or Analyst. "
        "Filtering is limited to an exact display code and allowlisted status. The "
        "workspace is always resolved from the authenticated session."
    ),
)
def query_transactions(request, filters: Query[TransactionQuery]):
    membership = _resolve_membership(request, "transaction", "query")
    queryset = Transaction.objects.filter(workspace_id=membership.workspace_id)
    if filters.code is not None:
        queryset = queryset.filter(code__iexact=filters.code.strip())
    if filters.status is not None:
        queryset = queryset.filter(status=filters.status)

    page = _page(queryset.order_by("-created_at", "-id"), filters)
    _log_query_allowed(request, membership, "transaction", page)
    return page


@operations_router.get(
    "/tickets",
    response={
        200: TicketPageOut,
        401: ErrorOut,
        403: ErrorOut,
    },
    operation_id="searchTickets",
    summary="Search synthetic support tickets",
    description=(
        "Searches fictional ticket codes and safe public details using fixed ORM "
        "filters and bounded pagination. Results are always restricted to the "
        "workspace resolved from the authenticated session."
    ),
)
def query_tickets(request, filters: Query[TicketQuery]):
    membership = _resolve_membership(request, "ticket", "query")
    queryset = Ticket.objects.filter(workspace_id=membership.workspace_id)
    if filters.query is not None:
        query = filters.query.strip()
        queryset = queryset.filter(
            Q(code__icontains=query) | Q(public_detail__icontains=query)
        )
    if filters.status is not None:
        queryset = queryset.filter(status=filters.status)

    page = _page(queryset.order_by("-created_at", "-id"), filters)
    _log_query_allowed(request, membership, "ticket", page)
    return page


@operations_router.get(
    "/transactions/{transaction_id}",
    response={
        200: TransactionOut,
        401: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
    },
    operation_id="getTransaction",
    summary="Get a synthetic transaction",
    description=(
        "Returns one fictional transaction for an Admin or Analyst. The workspace "
        "is resolved from the authenticated session; foreign and unknown IDs both "
        "return a generic not-found response."
    ),
)
def get_transaction(request, transaction_id: UUID):
    return _get_scoped_record(request, Transaction, transaction_id)


@operations_router.get(
    "/tickets/{ticket_id}",
    response={
        200: TicketOut,
        401: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
    },
    operation_id="getTicket",
    summary="Get a synthetic support ticket",
    description=(
        "Returns one fictional ticket for an Admin or Analyst. The workspace is "
        "resolved from the authenticated session; foreign and unknown IDs both "
        "return a generic not-found response."
    ),
)
def get_ticket(request, ticket_id: UUID):
    return _get_scoped_record(request, Ticket, ticket_id)
