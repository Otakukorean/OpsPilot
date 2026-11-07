import logging
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from ninja import Query, Router
from ninja.errors import HttpError

from apps.accounts.schemas import ErrorOut, ValidationErrorOut
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event

from .models import ChatMessage, ChatThread
from .permissions import resolve_active_membership
from .schemas import (
    CreateMessageIn,
    CreateThreadIn,
    AgentRunOut,
    MessageOut,
    MessagePageOut,
    PageQuery,
    ThreadOut,
    ThreadPageOut,
)
from apps.agents.services import create_agent_response
from apps.agents.security import AgentExecutionFailed, AgentRunRejected


audit_logger = logging.getLogger("opspilot.conversations")
conversations_router = Router(tags=["Conversations"])


def _resolve_membership(request, action):
    try:
        return resolve_active_membership(request.auth)
    except PermissionDenied:
        record_audit_event(
            request=request,
            action=f"conversations.{action}",
            outcome=AuditEvent.Outcome.DENIED,
            resource_type=action.split(".", 1)[0],
            reason="membership_inactive_or_missing",
        )
        audit_logger.warning(
            "Conversation access denied",
            extra={
                "event": f"conversations.{action}.denied",
                "request_id": request.request_id,
                "user_id": str(request.auth.pk),
                "outcome": "denied",
                "reason": "membership_inactive_or_missing",
            },
        )
        raise HttpError(403, "Conversation access denied.") from None


def _get_owned_thread(request, thread_id, action):
    membership = _resolve_membership(request, action)
    thread = ChatThread.objects.filter(
        id=thread_id,
        workspace_id=membership.workspace_id,
        owner_id=request.auth.pk,
    ).first()
    if thread is None:
        record_audit_event(
            request=request,
            action=f"conversations.{action}",
            outcome=AuditEvent.Outcome.DENIED,
            resource_type=action.split(".", 1)[0],
            reason="not_found_for_owner",
            workspace_id=membership.workspace_id,
        )
        audit_logger.warning(
            "Owned conversation not found",
            extra={
                "event": f"conversations.{action}.not_found",
                "request_id": request.request_id,
                "user_id": str(request.auth.pk),
                "workspace_id": str(membership.workspace_id),
                "role": membership.role,
                "outcome": "denied",
                "reason": "not_found_for_owner",
            },
        )
        raise HttpError(404, "Resource not found.")
    return thread, membership


def _page(queryset, page_query):
    total = queryset.count()
    items = list(
        queryset[page_query.offset : page_query.offset + page_query.limit]
    )
    return {
        "items": items,
        "total": total,
        "limit": page_query.limit,
        "offset": page_query.offset,
    }


def _serialize_message(message):
    return {
        "id": message.id,
        "role": message.role,
        "body": message.body,
        "status": message.status,
        "created_at": message.created_at,
        "citations": list(message.citations.all()),
    }


def _log_allowed(request, membership, action, **metadata):
    record_audit_event(
        request=request,
        action=f"conversations.{action}",
        outcome=AuditEvent.Outcome.ALLOWED,
        resource_type=action.split(".", 1)[0],
        workspace_id=membership.workspace_id,
    )
    audit_logger.info(
        "Conversation operation allowed",
        extra={
            "event": f"conversations.{action}.allowed",
            "request_id": request.request_id,
            "user_id": str(request.auth.pk),
            "workspace_id": str(membership.workspace_id),
            "role": membership.role,
            "outcome": "allowed",
            **metadata,
        },
    )


@conversations_router.post(
    "/chat/threads",
    response={
        201: ThreadOut,
        401: ErrorOut,
        403: ErrorOut,
        422: ValidationErrorOut,
    },
    operation_id="createChatThread",
    summary="Create a conversation",
    description=(
        "Creates a conversation owned by the authenticated user in the workspace "
        "resolved from their active membership."
    ),
)
def create_thread(request, payload: CreateThreadIn):
    membership = _resolve_membership(request, "thread.create")
    with transaction.atomic():
        thread = ChatThread.objects.create(
            workspace_id=membership.workspace_id,
            owner=request.auth,
            title=payload.title.strip(),
        )
        _log_allowed(request, membership, "thread.create")
    return 201, thread


@conversations_router.get(
    "/chat/threads",
    response={
        200: ThreadPageOut,
        401: ErrorOut,
        403: ErrorOut,
        422: ValidationErrorOut,
    },
    operation_id="listChatThreads",
    summary="List owned conversations",
    description=(
        "Returns only conversations owned by the authenticated user in their "
        "server-resolved active workspace."
    ),
)
def list_threads(request, page_query: Query[PageQuery]):
    membership = _resolve_membership(request, "thread.list")
    queryset = ChatThread.objects.filter(
        workspace_id=membership.workspace_id,
        owner_id=request.auth.pk,
    ).order_by("-updated_at", "-id")
    page = _page(queryset, page_query)
    _log_allowed(
        request,
        membership,
        "thread.list",
        result_count=len(page["items"]),
        limit=page["limit"],
        offset=page["offset"],
    )
    return page


@conversations_router.get(
    "/chat/threads/{thread_id}",
    response={
        200: ThreadOut,
        401: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
    },
    operation_id="getChatThread",
    summary="Get an owned conversation",
)
def get_thread(request, thread_id: UUID):
    thread, membership = _get_owned_thread(request, thread_id, "thread.read")
    _log_allowed(request, membership, "thread.read")
    return thread


@conversations_router.delete(
    "/chat/threads/{thread_id}",
    response={
        204: None,
        401: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
    },
    operation_id="deleteChatThread",
    summary="Delete an owned conversation",
    description=(
        "Permanently deletes an owned conversation and its messages. Ownership and "
        "workspace are resolved entirely from authenticated server state."
    ),
)
def delete_thread(request, thread_id: UUID):
    thread, membership = _get_owned_thread(request, thread_id, "thread.delete")
    with transaction.atomic():
        thread.delete()
        _log_allowed(request, membership, "thread.delete")
    return 204, None


@conversations_router.get(
    "/chat/threads/{thread_id}/messages",
    response={
        200: MessagePageOut,
        401: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
        422: ValidationErrorOut,
    },
    operation_id="listChatMessages",
    summary="List messages in an owned conversation",
)
def list_messages(request, thread_id: UUID, page_query: Query[PageQuery]):
    thread, membership = _get_owned_thread(request, thread_id, "message.list")
    page = _page(
        thread.messages.prefetch_related("citations").order_by("created_at", "id"),
        page_query,
    )
    page["items"] = [_serialize_message(message) for message in page["items"]]
    _log_allowed(
        request,
        membership,
        "message.list",
        result_count=len(page["items"]),
        limit=page["limit"],
        offset=page["offset"],
    )
    return page


@conversations_router.post(
    "/chat/threads/{thread_id}/messages",
    response={
        201: MessageOut,
        401: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
        422: ValidationErrorOut,
    },
    operation_id="createChatMessage",
    summary="Store a user message",
    description=(
        "Stores one user-authored message. This milestone does not call an LLM, "
        "generate an assistant response, perform RAG, or stream output."
    ),
)
def create_message(request, thread_id: UUID, payload: CreateMessageIn):
    thread, membership = _get_owned_thread(request, thread_id, "message.create")
    with transaction.atomic():
        message = ChatMessage.objects.create(
            thread=thread,
            role=ChatMessage.Role.USER,
            body=payload.text.strip(),
            status=ChatMessage.Status.STORED,
        )
        ChatThread.objects.filter(pk=thread.pk).update(updated_at=timezone.now())
        _log_allowed(request, membership, "message.create")
    return 201, _serialize_message(message)


@conversations_router.post(
    "/chat/threads/{thread_id}/agent-runs",
    response={
        201: AgentRunOut,
        401: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
        429: ErrorOut,
        503: ErrorOut,
        422: ValidationErrorOut,
    },
    operation_id="createAgentRun",
    summary="Generate a grounded assistant response",
    description=(
        "Runs the bounded, read-only P3 agent for an owned conversation. Identity, "
        "workspace, role, tool authorization, and citations are validated by the server."
    ),
)
def create_agent_run(request, thread_id: UUID, payload: CreateMessageIn):
    thread, membership = _get_owned_thread(request, thread_id, "agent.create")
    try:
        run, message = create_agent_response(
            request=request,
            thread=thread,
            membership=membership,
            question=payload.text.strip(),
        )
    except AgentRunRejected as exc:
        audit_logger.warning(
            "Agent run rejected by usage policy",
            extra={
                "event": "agent.run.rejected",
                "request_id": request.request_id,
                "user_id": str(request.auth.pk),
                "workspace_id": str(membership.workspace_id),
                "outcome": "denied",
                "reason": exc.reason,
            },
        )
        raise HttpError(429, exc.message) from None
    except AgentExecutionFailed as exc:
        audit_logger.warning(
            "Agent run failed",
            extra={
                "event": "agent.run.failed",
                "request_id": request.request_id,
                "user_id": str(request.auth.pk),
                "workspace_id": str(membership.workspace_id),
                "outcome": "denied",
                "reason": exc.reason,
            },
        )
        raise HttpError(503, "The assistant is temporarily unavailable.") from None
    except Exception:
        audit_logger.exception(
            "Unexpected agent service failure",
            extra={
                "event": "agent.run.failed",
                "request_id": request.request_id,
                "user_id": str(request.auth.pk),
                "workspace_id": str(membership.workspace_id),
                "outcome": "denied",
                "reason": "unexpected_service_error",
            },
        )
        raise HttpError(503, "The assistant is temporarily unavailable.") from None
    return 201, {
        "id": run.id,
        "status": run.status,
        "model": run.model,
        "llm_calls": run.llm_calls,
        "tool_calls": run.tool_calls,
        "input_tokens": run.input_tokens,
        "output_tokens": run.output_tokens,
        "message": _serialize_message(message),
        "citations": list(message.citations.all()),
    }
