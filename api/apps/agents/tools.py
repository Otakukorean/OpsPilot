import json
import time
from dataclasses import dataclass
from uuid import UUID

from django.db.models import Q
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apps.accounts.models import Membership
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.knowledge.retrieval import search_authorized_knowledge
from apps.operations.models import Ticket, Transaction

from .models import ToolInvocation


class SearchKnowledgeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=1_000)
    limit: int = Field(ge=1, le=5)


class GetTransactionArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction_id: str = Field(min_length=1, max_length=64)


class SearchTicketsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=200)
    limit: int = Field(ge=1, le=5)


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": (
                "Search authorized synthetic workspace knowledge. Preserve an exact "
                "document title from the user's request in the search query."
            ),
            "strict": True,
            "parameters": SearchKnowledgeArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_transaction",
            "description": "Get one authorized synthetic transaction by UUID or display code.",
            "strict": True,
            "parameters": GetTransactionArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_tickets",
            "description": "Search authorized synthetic support tickets.",
            "strict": True,
            "parameters": SearchTicketsArgs.model_json_schema(),
        },
    },
]


@dataclass(frozen=True)
class CitationEvidence:
    document_id: UUID
    chunk_id: UUID
    title: str
    page: int | None
    excerpt: str


@dataclass(frozen=True)
class ToolResult:
    content: str
    outcome: str
    reason: str
    has_evidence: bool
    citations: tuple[CitationEvidence, ...] = ()


class ToolExecutor:
    """Execute only fixed read-only tools using freshly resolved server identity."""

    def __init__(self, *, actor, run, request):
        self.actor = actor
        self.run = run
        self.request = request

    def execute(self, name, arguments):
        started = time.monotonic()
        try:
            result = self._execute(name, arguments)
        except Exception:
            result = ToolResult(
                content=json.dumps({"error": "Tool execution failed safely."}),
                outcome=ToolInvocation.Outcome.ERROR,
                reason="internal_error",
                has_evidence=False,
            )
        duration_ms = max(0, round((time.monotonic() - started) * 1_000))
        ToolInvocation.objects.create(
            run=self.run,
            tool_name=name[:64],
            outcome=result.outcome,
            reason=result.reason,
            duration_ms=duration_ms,
        )
        audit_outcome = (
            AuditEvent.Outcome.ALLOWED
            if result.outcome == ToolInvocation.Outcome.ALLOWED
            else AuditEvent.Outcome.DENIED
        )
        record_audit_event(
            request=self.request,
            action=f"agent.tool.{name[:64]}",
            outcome=audit_outcome,
            resource_type="agent_tool",
            reason=result.reason,
            workspace_id=self.run.workspace_id,
        )
        return result

    def _membership(self):
        return (
            Membership.objects.filter(user=self.actor, is_active=True)
            .select_related("workspace")
            .first()
        )

    def _execute(self, name, arguments):
        membership = self._membership()
        if membership is None or membership.workspace_id != self.run.workspace_id:
            return self._denied("membership_changed")

        handlers = {
            "search_knowledge": (SearchKnowledgeArgs, self._search_knowledge),
            "get_transaction": (GetTransactionArgs, self._get_transaction),
            "search_tickets": (SearchTicketsArgs, self._search_tickets),
        }
        handler = handlers.get(name)
        if handler is None:
            return self._denied("tool_not_allowlisted")
        schema, callback = handler
        try:
            parsed = schema.model_validate(arguments)
        except ValidationError:
            return self._denied("invalid_arguments")
        return callback(membership, parsed)

    @staticmethod
    def _denied(reason):
        return ToolResult(
            content=json.dumps({"error": "Tool access denied."}),
            outcome=ToolInvocation.Outcome.DENIED,
            reason=reason,
            has_evidence=False,
        )

    def _search_knowledge(self, membership, args):
        evidence = search_authorized_knowledge(
            membership=membership, query=args.query, limit=args.limit
        )
        citations = tuple(
            CitationEvidence(
                document_id=item.document_id,
                chunk_id=item.chunk_id,
                title=item.title,
                page=item.page,
                excerpt=item.excerpt,
            )
            for item in evidence
        )
        rows = [
            {
                "source": f"K{index}",
                "title": item.title,
                "page": item.page,
                "excerpt": item.excerpt,
                "similarity": item.score,
            }
            for index, item in enumerate(evidence, start=1)
        ]
        return ToolResult(
            content=json.dumps({"results": rows}),
            outcome=ToolInvocation.Outcome.ALLOWED,
            reason="",
            has_evidence=bool(rows),
            citations=citations,
        )

    def _get_transaction(self, membership, args):
        if membership.role not in {Membership.Role.ADMIN, Membership.Role.ANALYST}:
            return self._denied("role_not_allowed")
        query = Q(code__iexact=args.transaction_id.strip())
        try:
            query |= Q(id=UUID(args.transaction_id))
        except (ValueError, AttributeError):
            pass
        record = Transaction.objects.filter(
            query, workspace_id=membership.workspace_id
        ).first()
        if record is None:
            return ToolResult(
                content=json.dumps({"error": "Resource not found."}),
                outcome=ToolInvocation.Outcome.NOT_FOUND,
                reason="not_found_in_workspace",
                has_evidence=False,
            )
        return ToolResult(
            content=json.dumps(
                {
                    "transaction": {
                        "code": record.code,
                        "status": record.status,
                        "detail": record.public_detail,
                        "created_at": record.created_at.isoformat(),
                    }
                }
            ),
            outcome=ToolInvocation.Outcome.ALLOWED,
            reason="",
            has_evidence=True,
        )

    def _search_tickets(self, membership, args):
        if membership.role not in {Membership.Role.ADMIN, Membership.Role.ANALYST}:
            return self._denied("role_not_allowed")
        rows = list(
            Ticket.objects.filter(workspace_id=membership.workspace_id)
            .filter(
                Q(code__icontains=args.query.strip())
                | Q(public_detail__icontains=args.query.strip())
            )
            .order_by("-created_at", "-id")[: args.limit]
        )
        return ToolResult(
            content=json.dumps(
                {
                    "results": [
                        {
                            "code": row.code,
                            "status": row.status,
                            "detail": row.public_detail,
                            "created_at": row.created_at.isoformat(),
                        }
                        for row in rows
                    ]
                }
            ),
            outcome=ToolInvocation.Outcome.ALLOWED,
            reason="",
            has_evidence=bool(rows),
        )
