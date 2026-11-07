import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.conversations.models import ChatMessage, MessageCitation
from apps.knowledge.models import DocumentChunk
from apps.knowledge.permissions import permitted_visibilities

from .graph import run_agent
from .models import AgentRun
from .security import AgentExecutionFailed, AgentRunRejected, enforce_agent_run_limits
from .tools import ToolExecutor


def create_agent_response(*, request, thread, membership, question, model=None):
    """Persist a user turn, run the bounded graph, and validate citations again."""

    try:
        with transaction.atomic():
            get_user_model().objects.select_for_update().only("pk").get(
                pk=request.auth.pk
            )
            enforce_agent_run_limits(actor=request.auth)
            user_message = ChatMessage.objects.create(
                thread=thread,
                role=ChatMessage.Role.USER,
                body=question,
                status=ChatMessage.Status.STORED,
            )
            run = AgentRun.objects.create(
                workspace_id=membership.workspace_id,
                actor=request.auth,
                thread=thread,
                user_message=user_message,
                model=settings.OPENAI_CHAT_MODEL,
            )
    except AgentRunRejected as exc:
        record_audit_event(
            request=request,
            action="agent.run",
            outcome=AuditEvent.Outcome.DENIED,
            resource_type="agent_run",
            reason=exc.reason,
            workspace_id=membership.workspace_id,
        )
        raise

    started = time.monotonic()
    try:
        result = run_agent(
            question=question,
            executor=ToolExecutor(actor=request.auth, run=run, request=request),
            model=model,
        )
    except Exception as exc:
        error_code = (
            "provider_timeout"
            if isinstance(exc, TimeoutError) or "timeout" in type(exc).__name__.casefold()
            else "provider_or_graph_error"
        )
        run.status = AgentRun.Status.FAILED
        run.error_code = error_code
        run.duration_ms = max(0, round((time.monotonic() - started) * 1_000))
        run.completed_at = timezone.now()
        run.save(
            update_fields=["status", "error_code", "duration_ms", "completed_at"]
        )
        record_audit_event(
            request=request,
            action="agent.run",
            outcome=AuditEvent.Outcome.DENIED,
            resource_type="agent_run",
            reason=error_code,
            workspace_id=membership.workspace_id,
        )
        raise AgentExecutionFailed(error_code) from exc

    chunk_ids = [item.chunk_id for item in result["citations"]]
    allowed_chunks = {
        item.id: item
        for item in DocumentChunk.objects.filter(
            id__in=chunk_ids,
            workspace_id=membership.workspace_id,
            document__workspace_id=membership.workspace_id,
            document__status="ready",
            document__visibility__in=permitted_visibilities(membership.role),
        ).select_related("document")
    }

    with transaction.atomic():
        assistant = ChatMessage.objects.create(
            thread=thread,
            role=ChatMessage.Role.ASSISTANT,
            body=result["answer"],
            status=ChatMessage.Status.COMPLETED,
        )
        source_number = 1
        for evidence in result["citations"]:
            chunk = allowed_chunks.get(evidence.chunk_id)
            if chunk is None or chunk.document_id != evidence.document_id:
                continue
            MessageCitation.objects.create(
                message=assistant,
                document=chunk.document,
                chunk=chunk,
                source_number=source_number,
                title=chunk.document.title,
                page=chunk.page,
                excerpt=chunk.text[:300],
            )
            source_number += 1
        run.assistant_message = assistant
        run.status = AgentRun.Status.COMPLETED
        run.llm_calls = result["llm_calls"]
        run.tool_calls = result["tool_calls"]
        run.input_tokens = result["input_tokens"]
        run.output_tokens = result["output_tokens"]
        run.duration_ms = max(0, round((time.monotonic() - started) * 1_000))
        run.completed_at = timezone.now()
        run.save(
            update_fields=[
                "assistant_message", "status", "llm_calls", "tool_calls",
                "input_tokens", "output_tokens", "duration_ms", "completed_at",
            ]
        )
        thread.updated_at = timezone.now()
        thread.save(update_fields=["updated_at"])
        record_audit_event(
            request=request,
            action="agent.run",
            outcome=AuditEvent.Outcome.ALLOWED,
            resource_type="agent_run",
            workspace_id=membership.workspace_id,
        )
    return run, assistant
