from types import SimpleNamespace

from django.test import TestCase

from apps.accounts.models import Membership, User, Workspace
from apps.agents.models import AgentRun, ToolInvocation
from apps.agents.tools import TOOL_SCHEMAS, ToolExecutor
from apps.conversations.models import ChatMessage, ChatThread
from apps.operations.models import Ticket, Transaction


class AgentToolSecurityTests(TestCase):
    def test_strict_tool_schemas_require_every_declared_property(self):
        for tool in TOOL_SCHEMAS:
            with self.subTest(tool=tool["function"]["name"]):
                parameters = tool["function"]["parameters"]
                self.assertEqual(
                    set(parameters["required"]),
                    set(parameters["properties"]),
                )
                self.assertFalse(parameters["additionalProperties"])

    def setUp(self):
        self.atlas = Workspace.objects.create(name="Atlas Agent Tools")
        self.northstar = Workspace.objects.create(name="Northstar Agent Tools")
        self.analyst = User.objects.create_user(
            email="agent-analyst@atlas.example", password="synthetic-password"
        )
        self.viewer = User.objects.create_user(
            email="agent-viewer@atlas.example", password="synthetic-password"
        )
        Membership.objects.create(
            user=self.analyst, workspace=self.atlas, role=Membership.Role.ANALYST
        )
        Membership.objects.create(
            user=self.viewer, workspace=self.atlas, role=Membership.Role.VIEWER
        )
        self.own_transaction = Transaction.objects.create(
            workspace=self.atlas,
            code="TXN-AGENT-OWN",
            status=Transaction.Status.FAILED,
            public_detail="Allowed synthetic transaction detail.",
        )
        self.foreign_transaction = Transaction.objects.create(
            workspace=self.northstar,
            code="TXN-AGENT-FOREIGN",
            status=Transaction.Status.FAILED,
            public_detail="Never reveal this foreign synthetic detail.",
        )
        Ticket.objects.create(
            workspace=self.northstar,
            code="TKT-FOREIGN-SECRET",
            status=Ticket.Status.OPEN,
            public_detail="Never reveal this foreign ticket.",
        )

    def _executor(self, user):
        thread = ChatThread.objects.create(
            workspace=self.atlas, owner=user, title="Synthetic agent security"
        )
        message = ChatMessage.objects.create(
            thread=thread,
            role=ChatMessage.Role.USER,
            body="Synthetic question",
            status=ChatMessage.Status.STORED,
        )
        run = AgentRun.objects.create(
            workspace=self.atlas,
            actor=user,
            thread=thread,
            user_message=message,
            model="test-model",
        )
        request = SimpleNamespace(
            auth=user, user=user, request_id="00000000-0000-0000-0000-000000000001"
        )
        return ToolExecutor(actor=user, run=run, request=request), run

    def test_analyst_cannot_read_foreign_transaction_by_guessed_uuid_or_code(self):
        executor, run = self._executor(self.analyst)

        by_uuid = executor.execute(
            "get_transaction", {"transaction_id": str(self.foreign_transaction.id)}
        )
        by_code = executor.execute(
            "get_transaction", {"transaction_id": self.foreign_transaction.code}
        )

        self.assertFalse(by_uuid.has_evidence)
        self.assertFalse(by_code.has_evidence)
        self.assertNotIn("Never reveal", by_uuid.content + by_code.content)
        self.assertEqual(
            run.tool_invocations.filter(outcome=ToolInvocation.Outcome.NOT_FOUND).count(),
            2,
        )

    def test_viewer_is_denied_transaction_tool_before_record_is_returned(self):
        executor, run = self._executor(self.viewer)

        result = executor.execute(
            "get_transaction", {"transaction_id": str(self.own_transaction.id)}
        )

        self.assertFalse(result.has_evidence)
        self.assertNotIn(self.own_transaction.public_detail, result.content)
        invocation = run.tool_invocations.get()
        self.assertEqual(invocation.outcome, ToolInvocation.Outcome.DENIED)
        self.assertEqual(invocation.reason, "role_not_allowed")

    def test_workspace_argument_injection_and_unknown_tools_are_denied(self):
        executor, run = self._executor(self.analyst)

        injected = executor.execute(
            "get_transaction",
            {
                "transaction_id": str(self.own_transaction.id),
                "workspace_id": str(self.northstar.id),
            },
        )
        unknown = executor.execute("request_url", {"url": "https://attacker.invalid"})

        self.assertFalse(injected.has_evidence)
        self.assertFalse(unknown.has_evidence)
        self.assertEqual(
            set(run.tool_invocations.values_list("reason", flat=True)),
            {"invalid_arguments", "tool_not_allowlisted"},
        )

    def test_ticket_search_never_returns_foreign_workspace_rows(self):
        executor, _ = self._executor(self.analyst)

        result = executor.execute(
            "search_tickets", {"query": "FOREIGN-SECRET", "limit": 5}
        )

        self.assertFalse(result.has_evidence)
        self.assertNotIn("Never reveal", result.content)
