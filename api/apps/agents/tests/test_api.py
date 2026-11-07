import json
from unittest.mock import patch

from django.conf import settings
from django.test import Client, TestCase, override_settings

from apps.accounts.models import Membership, User, Workspace
from apps.agents.models import AgentRun
from apps.audit.models import AuditEvent
from apps.agents.tools import CitationEvidence
from apps.conversations.models import ChatThread, MessageCitation
from apps.knowledge.models import Document, DocumentChunk


class AgentRunAPITests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.atlas = Workspace.objects.create(name="Atlas Agent API")
        self.northstar = Workspace.objects.create(name="Northstar Agent API")
        self.owner = self._user("agent-owner@atlas.example", self.atlas)
        self.other = self._user("agent-other@atlas.example", self.atlas)
        self.foreign = self._user("agent-owner@northstar.example", self.northstar)
        self.thread = ChatThread.objects.create(
            workspace=self.atlas, owner=self.owner, title="Owned agent thread"
        )
        self.other_thread = ChatThread.objects.create(
            workspace=self.atlas, owner=self.other, title="Other agent thread"
        )
        self.foreign_thread = ChatThread.objects.create(
            workspace=self.northstar, owner=self.foreign, title="Foreign agent thread"
        )

    @staticmethod
    def _user(email, workspace):
        user = User.objects.create_user(email=email, password="synthetic-password")
        Membership.objects.create(
            user=user, workspace=workspace, role=Membership.Role.ANALYST
        )
        return user

    def _url(self, thread):
        return f"/api/v1/chat/threads/{thread.id}/agent-runs"

    def _authenticate(self):
        self.client.force_login(self.owner)
        self.client.get("/api/v1/auth/csrf")
        return self.client.cookies[settings.CSRF_COOKIE_NAME].value

    def _post(self, thread, token, text="Explain the synthetic failure"):
        return self.client.post(
            self._url(thread),
            data=json.dumps({"text": text}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

    def test_agent_endpoint_requires_authentication_and_csrf(self):
        self.client.get("/api/v1/auth/csrf")
        anonymous_token = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        unauthenticated = self.client.post(
            self._url(self.thread),
            data=json.dumps({"text": "Synthetic question"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=anonymous_token,
        )
        self.client.force_login(self.owner)
        missing_csrf = self.client.post(
            self._url(self.thread),
            data=json.dumps({"text": "Synthetic question"}),
            content_type="application/json",
        )

        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(missing_csrf.status_code, 403)

    def test_openapi_uses_the_agent_citation_contract(self):
        schema = self.client.get("/api/v1/openapi.json").json()

        citation = schema["components"]["schemas"]["AgentCitationOut"]

        self.assertEqual(
            set(citation["properties"]),
            {"source_number", "title", "page", "excerpt"},
        )

    def test_cannot_run_agent_on_another_users_or_workspaces_thread(self):
        token = self._authenticate()

        for thread in (self.other_thread, self.foreign_thread):
            with self.subTest(thread=thread.id):
                response = self._post(thread, token)
                self.assertEqual(response.status_code, 404)
        self.assertFalse(AgentRun.objects.exists())

    @patch("apps.agents.services.run_agent")
    def test_server_revalidates_and_drops_foreign_citation(self, mocked_run):
        foreign_document = Document.objects.create(
            workspace=self.northstar,
            uploaded_by=self.foreign,
            title="Foreign synthetic playbook",
            source_file="knowledge/foreign/source.pdf",
            original_filename="foreign.pdf",
            content_type="application/pdf",
            size_bytes=10,
            sha256="a" * 64,
            status=Document.Status.READY,
            visibility=Document.Visibility.VIEWER,
            embedding_model="local_hashing_v1",
        )
        foreign_chunk = DocumentChunk.objects.create(
            document=foreign_document,
            workspace=self.northstar,
            document_version=1,
            page=1,
            chunk_index=0,
            text="Never reveal this foreign citation.",
            embedding=[0.0] * 384,
        )
        mocked_run.return_value = {
            "answer": "Synthetic answer.",
            "citations": [
                CitationEvidence(
                    document_id=foreign_document.id,
                    chunk_id=foreign_chunk.id,
                    title=foreign_document.title,
                    page=1,
                    excerpt=foreign_chunk.text,
                )
            ],
            "llm_calls": 2,
            "tool_calls": 1,
            "input_tokens": 20,
            "output_tokens": 5,
        }
        token = self._authenticate()

        response = self._post(self.thread, token)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["citations"], [])
        self.assertFalse(MessageCitation.objects.exists())
        self.assertNotIn("foreign", json.dumps(response.json()).lower())

    @patch("apps.agents.services.run_agent")
    def test_server_revalidates_and_drops_restricted_citation(self, mocked_run):
        restricted_document = Document.objects.create(
            workspace=self.atlas,
            uploaded_by=self.owner,
            title="Restricted synthetic playbook",
            source_file="knowledge/restricted/source.pdf",
            original_filename="restricted.pdf",
            content_type="application/pdf",
            size_bytes=10,
            sha256="b" * 64,
            status=Document.Status.READY,
            visibility=Document.Visibility.RESTRICTED,
            embedding_model="local_hashing_v1",
        )
        restricted_chunk = DocumentChunk.objects.create(
            document=restricted_document,
            workspace=self.atlas,
            document_version=1,
            page=1,
            chunk_index=0,
            text="restricted-marker must not become a citation",
            embedding=[0.0] * 384,
        )
        mocked_run.return_value = {
            "answer": "Synthetic answer without private content.",
            "citations": [
                CitationEvidence(
                    document_id=restricted_document.id,
                    chunk_id=restricted_chunk.id,
                    title=restricted_document.title,
                    page=1,
                    excerpt=restricted_chunk.text,
                )
            ],
            "llm_calls": 2,
            "tool_calls": 1,
            "input_tokens": 20,
            "output_tokens": 5,
        }
        token = self._authenticate()

        response = self._post(self.thread, token)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["citations"], [])
        self.assertNotIn("restricted-marker", response.content.decode())
        self.assertFalse(MessageCitation.objects.exists())

    @patch("apps.agents.services.run_agent", side_effect=RuntimeError("provider down"))
    def test_provider_failure_returns_safe_error_and_marks_run_failed(self, _mocked):
        token = self._authenticate()

        response = self._post(self.thread, token, text="private synthetic question")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "REQUEST_ERROR")
        self.assertNotIn("provider down", response.content.decode())
        run = AgentRun.objects.get()
        self.assertEqual(run.status, AgentRun.Status.FAILED)
        self.assertEqual(run.error_code, "provider_or_graph_error")

    @patch("apps.agents.services.run_agent", side_effect=TimeoutError("synthetic timeout"))
    def test_provider_timeout_is_sanitized_and_classified(self, _mocked):
        token = self._authenticate()

        response = self._post(self.thread, token, text="synthetic timeout question")

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("synthetic timeout", response.content.decode())
        run = AgentRun.objects.get()
        self.assertEqual(run.error_code, "provider_timeout")
        self.assertTrue(
            AuditEvent.objects.filter(
                action="agent.run",
                outcome=AuditEvent.Outcome.DENIED,
                reason="provider_timeout",
            ).exists()
        )

    @override_settings(
        AGENT_RATE_LIMIT_REQUESTS=1,
        AGENT_RATE_LIMIT_WINDOW_SECONDS=3600,
        AGENT_MAX_CONCURRENT_RUNS=2,
        AGENT_USER_TOKEN_BUDGET=100_000,
        AGENT_TOKEN_BUDGET_WINDOW_SECONDS=86_400,
    )
    def test_per_user_request_limit_rejects_before_storing_question(self):
        AgentRun.objects.create(
            workspace=self.atlas,
            actor=self.owner,
            thread=self.thread,
            model="synthetic-test-model",
            status=AgentRun.Status.COMPLETED,
        )
        token = self._authenticate()

        response = self._post(self.thread, token, text="must not be stored")

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["code"], "RATE_LIMITED")
        self.assertNotIn("must not be stored", response.content.decode())
        self.assertFalse(self.thread.messages.filter(body="must not be stored").exists())
        self.assertTrue(
            AuditEvent.objects.filter(
                action="agent.run",
                reason="request_rate_limit",
            ).exists()
        )

    @override_settings(
        AGENT_RATE_LIMIT_REQUESTS=20,
        AGENT_MAX_CONCURRENT_RUNS=2,
        AGENT_USER_TOKEN_BUDGET=100,
        AGENT_TOKEN_BUDGET_WINDOW_SECONDS=86_400,
    )
    def test_per_user_token_budget_rejects_before_provider_call(self):
        AgentRun.objects.create(
            workspace=self.atlas,
            actor=self.owner,
            thread=self.thread,
            model="synthetic-test-model",
            status=AgentRun.Status.COMPLETED,
            input_tokens=80,
            output_tokens=20,
        )
        token = self._authenticate()

        with patch("apps.agents.services.run_agent") as mocked_run:
            response = self._post(self.thread, token)

        self.assertEqual(response.status_code, 429)
        mocked_run.assert_not_called()
        self.assertTrue(
            AuditEvent.objects.filter(reason="token_budget_limit").exists()
        )

    @override_settings(
        AGENT_RATE_LIMIT_REQUESTS=20,
        AGENT_MAX_CONCURRENT_RUNS=1,
        AGENT_USER_TOKEN_BUDGET=100_000,
    )
    def test_concurrent_run_limit_rejects_before_provider_call(self):
        AgentRun.objects.create(
            workspace=self.atlas,
            actor=self.owner,
            thread=self.thread,
            model="synthetic-test-model",
            status=AgentRun.Status.PENDING,
        )
        token = self._authenticate()

        with patch("apps.agents.services.run_agent") as mocked_run:
            response = self._post(self.thread, token)

        self.assertEqual(response.status_code, 429)
        mocked_run.assert_not_called()
        self.assertTrue(
            AuditEvent.objects.filter(reason="concurrent_run_limit").exists()
        )
