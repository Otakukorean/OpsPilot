import logging
from uuid import UUID

from django.core.exceptions import PermissionDenied
from ninja import File, Form, Query, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

from apps.accounts.models import Membership
from apps.accounts.schemas import ErrorOut, ValidationErrorOut
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event

from .models import Document
from .permissions import (
    permitted_visibilities,
    require_admin_membership,
    resolve_knowledge_membership,
)
from .retrieval import search_authorized_knowledge
from .schemas import (
    DocumentOut,
    DocumentPageOut,
    PageQuery,
    SearchKnowledgeIn,
    SearchKnowledgeOut,
    UpdateVisibilityIn,
)
from .services import create_document, delete_document
from .validation import InvalidDocument, validate_upload


logger = logging.getLogger("opspilot.knowledge")
knowledge_router = Router(tags=["Knowledge"])


def _audit(request, membership, action, outcome, reason="", **metadata):
    record_audit_event(
        request=request,
        action=f"knowledge.{action}",
        outcome=outcome,
        resource_type="document",
        reason=reason,
        workspace_id=membership.workspace_id if membership else None,
    )
    logger.log(
        logging.INFO if outcome == AuditEvent.Outcome.ALLOWED else logging.WARNING,
        "Knowledge operation",
        extra={
            "event": f"knowledge.{action}.{outcome}",
            "request_id": request.request_id,
            "user_id": str(request.auth.pk),
            "workspace_id": str(membership.workspace_id) if membership else None,
            "role": membership.role if membership else None,
            "outcome": outcome,
            "reason": reason,
            **metadata,
        },
    )


def _membership(request, *, admin=False, action):
    try:
        return (
            require_admin_membership(request.auth)
            if admin
            else resolve_knowledge_membership(request.auth)
        )
    except PermissionDenied:
        membership = (
            request.auth.memberships.filter(is_active=True).first()
            if request.auth.is_authenticated
            else None
        )
        reason = "admin_role_required" if admin else "membership_inactive_or_missing"
        _audit(request, membership, action, AuditEvent.Outcome.DENIED, reason)
        raise HttpError(403, "Knowledge access denied.") from None


def _scoped_document(request, document_id, *, admin, action):
    membership = _membership(request, admin=admin, action=action)
    queryset = Document.objects.filter(
        id=document_id,
        workspace_id=membership.workspace_id,
    )
    if not admin and membership.role != Membership.Role.ADMIN:
        queryset = queryset.filter(
            visibility__in=permitted_visibilities(membership.role)
        )
    document = queryset.first()
    if document is None:
        _audit(
            request,
            membership,
            action,
            AuditEvent.Outcome.DENIED,
            "not_found_in_workspace_or_visibility",
        )
        raise HttpError(404, "Resource not found.")
    return document, membership


@knowledge_router.post(
    "/documents",
    response={
        201: DocumentOut,
        401: ErrorOut,
        403: ErrorOut,
        422: ErrorOut,
    },
    operation_id="uploadDocument",
    summary="Upload a private knowledge document",
    description=(
        "Admin-only PDF/TXT upload. The backend validates content and stores it "
        "outside the public web root. Visibility always starts as restricted, and "
        "ingestion runs asynchronously."
    ),
)
def upload_document(
    request,
    file: File[UploadedFile],
    title: Form[str] = "",
):
    membership = _membership(request, admin=True, action="document.upload")
    try:
        validated = validate_upload(file)
    except InvalidDocument as exc:
        _audit(
            request,
            membership,
            "document.upload",
            AuditEvent.Outcome.DENIED,
            exc.code,
        )
        return 422, {
            "code": "INVALID_DOCUMENT",
            "message": str(exc),
            "request_id": request.request_id,
        }

    document = create_document(
        membership=membership,
        actor=request.auth,
        title=title,
        original_filename=file.name,
        validated=validated,
    )
    _audit(
        request,
        membership,
        "document.upload",
        AuditEvent.Outcome.ALLOWED,
        document_id=str(document.id),
        size_bytes=document.size_bytes,
    )
    return 201, document


@knowledge_router.get(
    "/documents",
    response={200: DocumentPageOut, 401: ErrorOut, 403: ErrorOut, 422: ValidationErrorOut},
    operation_id="listDocuments",
    summary="List visible knowledge documents",
)
def list_documents(request, page: Query[PageQuery]):
    membership = _membership(request, action="document.list")
    queryset = Document.objects.filter(workspace_id=membership.workspace_id)
    if membership.role != Membership.Role.ADMIN:
        queryset = queryset.filter(
            visibility__in=permitted_visibilities(membership.role)
        )
    total = queryset.count()
    items = list(queryset[page.offset : page.offset + page.limit])
    _audit(
        request,
        membership,
        "document.list",
        AuditEvent.Outcome.ALLOWED,
        result_count=len(items),
    )
    return {"items": items, "total": total, "limit": page.limit, "offset": page.offset}


@knowledge_router.get(
    "/documents/{document_id}",
    response={200: DocumentOut, 401: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    operation_id="getDocument",
    summary="Get permitted document metadata",
)
def get_document(request, document_id: UUID):
    document, membership = _scoped_document(
        request,
        document_id,
        admin=False,
        action="document.read",
    )
    _audit(request, membership, "document.read", AuditEvent.Outcome.ALLOWED)
    return document


@knowledge_router.patch(
    "/documents/{document_id}/visibility",
    response={
        200: DocumentOut,
        401: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
        422: ValidationErrorOut,
    },
    operation_id="publishDocument",
    summary="Publish or restrict a document",
    description=(
        "Admin-only visibility update. Restricted means unpublished; role values "
        "publish to that role and higher-privileged roles in the same workspace."
    ),
)
def update_document_visibility(request, document_id: UUID, payload: UpdateVisibilityIn):
    document, membership = _scoped_document(
        request,
        document_id,
        admin=True,
        action="document.publish",
    )
    document.visibility = payload.visibility
    document.save(update_fields=["visibility", "updated_at"])
    _audit(request, membership, "document.publish", AuditEvent.Outcome.ALLOWED)
    return document


@knowledge_router.delete(
    "/documents/{document_id}",
    response={204: None, 401: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    operation_id="deleteDocument",
    summary="Delete a document and its indexed content",
)
def remove_document(request, document_id: UUID):
    document, membership = _scoped_document(
        request,
        document_id,
        admin=True,
        action="document.delete",
    )
    delete_document(document)
    _audit(request, membership, "document.delete", AuditEvent.Outcome.ALLOWED)
    return 204, None


@knowledge_router.get(
    "/knowledge/search",
    response={
        200: SearchKnowledgeOut,
        401: ErrorOut,
        403: ErrorOut,
        422: ValidationErrorOut,
    },
    operation_id="searchKnowledge",
    summary="Search authorized knowledge",
    description=(
        "Returns bounded citation-ready evidence only after SQL filtering by the "
        "server-resolved workspace, ingestion state, and published role visibility."
    ),
)
def search_knowledge(request, payload: Query[SearchKnowledgeIn]):
    membership = _membership(request, action="document.search")
    evidence = search_authorized_knowledge(
        membership=membership,
        query=payload.query,
        limit=payload.limit,
    )
    _audit(
        request,
        membership,
        "document.search",
        AuditEvent.Outcome.ALLOWED,
        result_count=len(evidence),
    )
    return {
        "evidence": evidence,
        "insufficient_evidence": not evidence,
    }
