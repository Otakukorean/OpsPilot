import io
import json
import logging

from django.conf import settings
from django.test import Client, TestCase

from apps.accounts.models import Membership, User, Workspace
from apps.audit.models import AuditEvent
from apps.conversations.models import ChatMessage, ChatThread
from config.logging import JsonFormatter


class ConversationsAPITests(TestCase):
    threads_url = "/api/v1/chat/threads"

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.atlas = Workspace.objects.create(name="Atlas Conversations")
        self.northstar = Workspace.objects.create(name="Northstar Conversations")
        self.owner = self._create_user("owner@atlas.example", self.atlas)
        self.same_workspace_user = self._create_user(
            "other@atlas.example",
            self.atlas,
        )
        self.foreign_user = self._create_user(
            "owner@northstar.example",
            self.northstar,
        )
        self.user_without_membership = User.objects.create_user(
            email="no-membership@example.com",
            password="synthetic-password",
        )

        self.owned_thread = ChatThread.objects.create(
            workspace=self.atlas,
            owner=self.owner,
            title="Owned synthetic thread",
        )
        self.same_workspace_thread = ChatThread.objects.create(
            workspace=self.atlas,
            owner=self.same_workspace_user,
            title="Other user's synthetic thread",
        )
        self.foreign_thread = ChatThread.objects.create(
            workspace=self.northstar,
            owner=self.foreign_user,
            title="Foreign synthetic thread",
        )
        self.owned_message = ChatMessage.objects.create(
            thread=self.owned_thread,
            role=ChatMessage.Role.USER,
            body="Owned synthetic message.",
            status=ChatMessage.Status.STORED,
        )
        ChatMessage.objects.create(
            thread=self.foreign_thread,
            role=ChatMessage.Role.USER,
            body="Foreign synthetic message.",
            status=ChatMessage.Status.STORED,
        )

    def _create_user(self, email, workspace):
        user = User.objects.create_user(email=email, password="synthetic-password")
        Membership.objects.create(
            user=user,
            workspace=workspace,
            role=Membership.Role.ANALYST,
        )
        return user

    def _thread_url(self, thread):
        return f"{self.threads_url}/{thread.id}"

    def _messages_url(self, thread):
        return f"{self._thread_url(thread)}/messages"

    def _authenticate(self, user):
        self.client.force_login(user)
        response = self.client.get("/api/v1/auth/csrf")
        self.assertEqual(response.status_code, 200)
        return self.client.cookies[settings.CSRF_COOKIE_NAME].value

    def _post_json(self, url, payload, csrf_token):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

    def test_unauthenticated_conversation_endpoints_return_401(self):
        for url in (
            self.threads_url,
            self._thread_url(self.owned_thread),
            self._messages_url(self.owned_thread),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()["code"], "AUTHENTICATION_REQUIRED")

    def test_create_thread_uses_session_owner_and_workspace(self):
        csrf_token = self._authenticate(self.owner)

        response = self._post_json(
            self.threads_url,
            {"title": "  New synthetic investigation  "},
            csrf_token,
        )

        self.assertEqual(response.status_code, 201)
        thread = ChatThread.objects.get(id=response.json()["id"])
        self.assertEqual(thread.title, "New synthetic investigation")
        self.assertEqual(thread.owner, self.owner)
        self.assertEqual(thread.workspace, self.atlas)
        self.assertNotIn("owner", response.json())
        self.assertNotIn("workspace", response.json())

    def test_conversation_writes_require_csrf(self):
        self.client.force_login(self.owner)

        thread_response = self.client.post(
            self.threads_url,
            data=json.dumps({"title": "Missing CSRF"}),
            content_type="application/json",
        )
        message_response = self.client.post(
            self._messages_url(self.owned_thread),
            data=json.dumps({"text": "Missing CSRF"}),
            content_type="application/json",
        )
        delete_response = self.client.delete(self._thread_url(self.owned_thread))

        self.assertEqual(thread_response.status_code, 403)
        self.assertEqual(message_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)

    def test_thread_list_returns_only_owned_workspace_threads(self):
        self.client.force_login(self.owner)
        ChatThread.objects.create(
            workspace=self.atlas,
            owner=self.owner,
            title="Second owned thread",
        )

        response = self.client.get(self.threads_url, {"limit": 1, "offset": 0})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 2)
        self.assertEqual(len(payload["items"]), 1)
        serialized = json.dumps(payload)
        self.assertNotIn(str(self.same_workspace_thread.id), serialized)
        self.assertNotIn(str(self.foreign_thread.id), serialized)

    def test_owner_can_read_thread_and_message_history(self):
        self.client.force_login(self.owner)

        thread_response = self.client.get(self._thread_url(self.owned_thread))
        message_response = self.client.get(
            self._messages_url(self.owned_thread),
            {"limit": 20, "offset": 0},
        )

        self.assertEqual(thread_response.status_code, 200)
        self.assertEqual(thread_response.json()["id"], str(self.owned_thread.id))
        self.assertEqual(message_response.status_code, 200)
        self.assertEqual(message_response.json()["total"], 1)
        self.assertEqual(
            message_response.json()["items"][0]["id"],
            str(self.owned_message.id),
        )
        self.assertEqual(message_response.json()["items"][0]["citations"], [])

    def test_same_workspace_and_foreign_threads_return_generic_404(self):
        self.client.force_login(self.owner)

        same_workspace_response = self.client.get(
            self._thread_url(self.same_workspace_thread)
        )
        foreign_response = self.client.get(self._thread_url(self.foreign_thread))

        for response in (same_workspace_response, foreign_response):
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["code"], "NOT_FOUND")
            self.assertEqual(response.json()["message"], "Resource not found.")

    def test_cannot_read_or_post_messages_to_unowned_thread(self):
        csrf_token = self._authenticate(self.owner)

        for thread in (self.same_workspace_thread, self.foreign_thread):
            with self.subTest(thread=thread.id):
                read_response = self.client.get(self._messages_url(thread))
                create_response = self._post_json(
                    self._messages_url(thread),
                    {"text": "Attempted synthetic message."},
                    csrf_token,
                )
                self.assertEqual(read_response.status_code, 404)
                self.assertEqual(create_response.status_code, 404)

    def test_post_message_stores_user_message_without_assistant_generation(self):
        csrf_token = self._authenticate(self.owner)

        response = self._post_json(
            self._messages_url(self.owned_thread),
            {"text": "  Why did the synthetic transaction fail?  "},
            csrf_token,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["role"], ChatMessage.Role.USER)
        self.assertEqual(response.json()["status"], ChatMessage.Status.STORED)
        self.assertEqual(response.json()["citations"], [])
        self.assertEqual(
            response.json()["body"],
            "Why did the synthetic transaction fail?",
        )
        self.assertEqual(self.owned_thread.messages.count(), 2)
        self.assertFalse(
            self.owned_thread.messages.filter(role=ChatMessage.Role.ASSISTANT).exists()
        )

    def test_owner_can_delete_thread_and_messages_with_audit_record(self):
        csrf_token = self._authenticate(self.owner)
        thread_id = self.owned_thread.id

        response = self.client.delete(
            self._thread_url(self.owned_thread),
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(ChatThread.objects.filter(id=thread_id).exists())
        self.assertFalse(ChatMessage.objects.filter(id=self.owned_message.id).exists())
        self.assertTrue(
            AuditEvent.objects.filter(
                actor=self.owner,
                workspace=self.atlas,
                action="conversations.thread.delete",
                outcome=AuditEvent.Outcome.ALLOWED,
            ).exists()
        )

    def test_cannot_delete_another_users_or_workspaces_thread(self):
        csrf_token = self._authenticate(self.owner)

        for thread in (self.same_workspace_thread, self.foreign_thread):
            with self.subTest(thread=thread.id):
                response = self.client.delete(
                    self._thread_url(thread),
                    HTTP_X_CSRFTOKEN=csrf_token,
                )
                self.assertEqual(response.status_code, 404)
                self.assertTrue(ChatThread.objects.filter(id=thread.id).exists())

        self.assertEqual(
            AuditEvent.objects.filter(
                actor=self.owner,
                action="conversations.thread.delete",
                outcome=AuditEvent.Outcome.DENIED,
                reason="not_found_for_owner",
            ).count(),
            2,
        )

    def test_missing_active_membership_returns_403(self):
        csrf_token = self._authenticate(self.user_without_membership)

        list_response = self.client.get(self.threads_url)
        create_response = self._post_json(
            self.threads_url,
            {"title": "Synthetic denied thread"},
            csrf_token,
        )

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(create_response.status_code, 403)

    def test_conversation_input_and_pagination_are_bounded(self):
        csrf_token = self._authenticate(self.owner)

        blank_title = self._post_json(
            self.threads_url,
            {"title": "   "},
            csrf_token,
        )
        blank_message = self._post_json(
            self._messages_url(self.owned_thread),
            {"text": "   "},
            csrf_token,
        )
        oversized_message = self._post_json(
            self._messages_url(self.owned_thread),
            {"text": "x" * 4_001},
            csrf_token,
        )
        oversized_page = self.client.get(self.threads_url, {"limit": 51})

        for response in (
            blank_title,
            blank_message,
            oversized_message,
            oversized_page,
        ):
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["code"], "VALIDATION_ERROR")

    def test_titles_messages_and_guessed_ids_are_not_logged(self):
        streams = (io.StringIO(), io.StringIO())
        loggers = (
            logging.getLogger("opspilot.conversations"),
            logging.getLogger("opspilot.request"),
        )
        handlers = []
        for logger, stream in zip(loggers, streams, strict=True):
            handler = logging.StreamHandler(stream)
            handler.setFormatter(JsonFormatter())
            logger.addHandler(handler)
            handlers.append(handler)

        message_text = "never-log-this-synthetic-message"
        csrf_token = self._authenticate(self.owner)
        try:
            create_response = self._post_json(
                self._messages_url(self.owned_thread),
                {"text": message_text},
                csrf_token,
            )
            denied_response = self.client.get(self._thread_url(self.foreign_thread))
        finally:
            for logger, handler in zip(loggers, handlers, strict=True):
                logger.removeHandler(handler)

        serialized_logs = "\n".join(stream.getvalue() for stream in streams)
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(denied_response.status_code, 404)
        self.assertNotIn(message_text, serialized_logs)
        self.assertNotIn(str(self.owned_thread.id), serialized_logs)
        self.assertNotIn(str(self.foreign_thread.id), serialized_logs)
        self.assertIn("<thread_id>", streams[1].getvalue())

    def test_openapi_documents_conversation_contract(self):
        schema = self.client.get("/api/v1/openapi.json").json()
        paths = schema["paths"]
        threads_path = next(path for path in paths if path.endswith("/chat/threads"))
        thread_path = next(
            path
            for path in paths
            if path.endswith("/chat/threads/{thread_id}")
        )
        messages_path = next(
            path
            for path in paths
            if path.endswith("/chat/threads/{thread_id}/messages")
        )

        self.assertEqual(set(paths[threads_path]), {"get", "post"})
        self.assertEqual(set(paths[thread_path]), {"get", "delete"})
        self.assertEqual(set(paths[messages_path]), {"get", "post"})
