import io
import json
import logging

from django.test import Client, TestCase

from apps.accounts.models import Membership, User, Workspace
from apps.operations.models import Ticket, Transaction
from config.logging import JsonFormatter


class OperationsAPITests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.atlas = Workspace.objects.create(name="Atlas Synthetic")
        self.northstar = Workspace.objects.create(name="Northstar Synthetic")

        self.analyst = self._create_user(
            "analyst@atlas.example",
            self.atlas,
            Membership.Role.ANALYST,
        )
        self.admin = self._create_user(
            "admin@atlas.example",
            self.atlas,
            Membership.Role.ADMIN,
        )
        self.viewer = self._create_user(
            "viewer@atlas.example",
            self.atlas,
            Membership.Role.VIEWER,
        )

        self.atlas_transaction = Transaction.objects.create(
            workspace=self.atlas,
            code="TXN-SHARED",
            status=Transaction.Status.FAILED,
            public_detail="Synthetic Atlas transaction detail.",
        )
        self.foreign_transaction = Transaction.objects.create(
            workspace=self.northstar,
            code="TXN-SHARED",
            status=Transaction.Status.COMPLETED,
            public_detail="Synthetic Northstar transaction detail.",
        )
        self.atlas_ticket = Ticket.objects.create(
            workspace=self.atlas,
            code="TKT-SHARED",
            status=Ticket.Status.OPEN,
            public_detail="Synthetic Atlas ticket detail.",
        )
        self.foreign_ticket = Ticket.objects.create(
            workspace=self.northstar,
            code="TKT-SHARED",
            status=Ticket.Status.RESOLVED,
            public_detail="Synthetic Northstar ticket detail.",
        )

    def _create_user(self, email, workspace, role):
        user = User.objects.create_user(email=email, password="synthetic-password")
        Membership.objects.create(user=user, workspace=workspace, role=role)
        return user

    def _transaction_url(self, transaction):
        return f"/api/v1/transactions/{transaction.id}"

    def _ticket_url(self, ticket):
        return f"/api/v1/tickets/{ticket.id}"

    def test_unauthenticated_operations_requests_return_401(self):
        for url in (
            self._transaction_url(self.atlas_transaction),
            self._ticket_url(self.atlas_ticket),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()["code"], "AUTHENTICATION_REQUIRED")

    def test_analyst_can_read_records_in_active_workspace(self):
        self.client.force_login(self.analyst)

        transaction_response = self.client.get(
            self._transaction_url(self.atlas_transaction)
        )
        ticket_response = self.client.get(self._ticket_url(self.atlas_ticket))

        self.assertEqual(transaction_response.status_code, 200)
        self.assertEqual(transaction_response.json()["code"], "TXN-SHARED")
        self.assertEqual(ticket_response.status_code, 200)
        self.assertEqual(ticket_response.json()["code"], "TKT-SHARED")
        self.assertNotIn("workspace", transaction_response.json())
        self.assertNotIn("workspace", ticket_response.json())

    def test_admin_can_read_records_in_active_workspace(self):
        self.client.force_login(self.admin)

        self.assertEqual(
            self.client.get(self._transaction_url(self.atlas_transaction)).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(self._ticket_url(self.atlas_ticket)).status_code,
            200,
        )

    def test_viewer_is_denied_operations_records(self):
        self.client.force_login(self.viewer)

        for url in (
            self._transaction_url(self.atlas_transaction),
            self._ticket_url(self.atlas_ticket),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["code"], "FORBIDDEN")

    def test_guessed_foreign_ids_return_generic_404_without_leakage(self):
        self.client.force_login(self.analyst)

        for foreign_record, url in (
            (
                self.foreign_transaction,
                self._transaction_url(self.foreign_transaction),
            ),
            (self.foreign_ticket, self._ticket_url(self.foreign_ticket)),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                body = response.content.decode()
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["code"], "NOT_FOUND")
                self.assertNotIn(foreign_record.code, body)
                self.assertNotIn(foreign_record.public_detail, body)

    def test_unknown_and_foreign_ids_have_same_response_shape(self):
        self.client.force_login(self.analyst)
        unknown_url = "/api/v1/transactions/00000000-0000-0000-0000-000000000001"

        unknown_response = self.client.get(unknown_url)
        foreign_response = self.client.get(
            self._transaction_url(self.foreign_transaction)
        )

        self.assertEqual(unknown_response.status_code, 404)
        self.assertEqual(foreign_response.status_code, 404)
        self.assertEqual(
            set(unknown_response.json()),
            set(foreign_response.json()),
        )
        self.assertEqual(unknown_response.json()["code"], "NOT_FOUND")
        self.assertEqual(foreign_response.json()["code"], "NOT_FOUND")

    def test_inactive_membership_is_denied(self):
        Membership.objects.filter(user=self.analyst).update(is_active=False)
        self.client.force_login(self.analyst)

        response = self.client.get(self._transaction_url(self.atlas_transaction))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "FORBIDDEN")

    def test_transaction_query_is_filtered_and_workspace_scoped(self):
        Transaction.objects.create(
            workspace=self.atlas,
            code="TXN-SECOND",
            status=Transaction.Status.COMPLETED,
            public_detail="Second synthetic Atlas transaction.",
        )
        self.client.force_login(self.analyst)

        response = self.client.get(
            "/api/v1/transactions",
            {"code": "txn-shared", "status": Transaction.Status.FAILED},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["id"], str(self.atlas_transaction.id))
        serialized = json.dumps(payload)
        self.assertNotIn(str(self.foreign_transaction.id), serialized)
        self.assertNotIn(self.foreign_transaction.public_detail, serialized)

    def test_ticket_search_is_scoped_and_paginated(self):
        first_match = Ticket.objects.create(
            workspace=self.atlas,
            code="TKT-NEEDLE-1",
            status=Ticket.Status.IN_PROGRESS,
            public_detail="Synthetic needle investigation one.",
        )
        second_match = Ticket.objects.create(
            workspace=self.atlas,
            code="TKT-NEEDLE-2",
            status=Ticket.Status.IN_PROGRESS,
            public_detail="Synthetic needle investigation two.",
        )
        Ticket.objects.create(
            workspace=self.northstar,
            code="TKT-NEEDLE-FOREIGN",
            status=Ticket.Status.IN_PROGRESS,
            public_detail="Foreign synthetic needle detail.",
        )
        self.client.force_login(self.analyst)

        first_page = self.client.get(
            "/api/v1/tickets",
            {
                "query": "needle",
                "status": Ticket.Status.IN_PROGRESS,
                "limit": 1,
                "offset": 0,
            },
        )
        second_page = self.client.get(
            "/api/v1/tickets",
            {
                "query": "needle",
                "status": Ticket.Status.IN_PROGRESS,
                "limit": 1,
                "offset": 1,
            },
        )

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(first_page.json()["total"], 2)
        self.assertEqual(second_page.json()["total"], 2)
        returned_ids = {
            first_page.json()["items"][0]["id"],
            second_page.json()["items"][0]["id"],
        }
        self.assertEqual(returned_ids, {str(first_match.id), str(second_match.id)})

    def test_query_endpoints_require_authentication_and_allowed_role(self):
        for url in ("/api/v1/transactions", "/api/v1/tickets"):
            with self.subTest(url=url, state="anonymous"):
                self.assertEqual(self.client.get(url).status_code, 401)

        self.client.force_login(self.viewer)
        for url in ("/api/v1/transactions", "/api/v1/tickets"):
            with self.subTest(url=url, state="viewer"):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_query_pagination_and_filters_are_bounded(self):
        self.client.force_login(self.analyst)

        oversized_page = self.client.get("/api/v1/transactions", {"limit": 51})
        invalid_status = self.client.get(
            "/api/v1/tickets",
            {"status": "not-a-real-status"},
        )
        blank_query = self.client.get("/api/v1/tickets", {"query": "   "})

        for response in (oversized_page, invalid_status, blank_query):
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["code"], "VALIDATION_ERROR")

    def test_ticket_query_text_is_not_written_to_audit_logs(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        logger = logging.getLogger("opspilot.operations")
        logger.addHandler(handler)
        self.client.force_login(self.analyst)
        search_text = "private-looking-synthetic-search"
        try:
            response = self.client.get(
                "/api/v1/tickets",
                {"query": search_text},
            )
        finally:
            logger.removeHandler(handler)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(search_text, stream.getvalue())

    def test_denied_foreign_record_data_is_not_written_to_structured_logs(self):
        streams = (io.StringIO(), io.StringIO())
        handlers = []
        loggers = (
            logging.getLogger("opspilot.operations"),
            logging.getLogger("opspilot.request"),
        )
        for logger, stream in zip(loggers, streams, strict=True):
            handler = logging.StreamHandler(stream)
            handler.setFormatter(JsonFormatter())
            logger.addHandler(handler)
            handlers.append(handler)

        self.client.force_login(self.analyst)
        try:
            response = self.client.get(
                self._transaction_url(self.foreign_transaction)
            )
        finally:
            for logger, handler in zip(loggers, handlers, strict=True):
                logger.removeHandler(handler)

        serialized_logs = "\n".join(stream.getvalue() for stream in streams)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(str(self.foreign_transaction.id), serialized_logs)
        self.assertNotIn(self.foreign_transaction.code, serialized_logs)
        self.assertNotIn(self.foreign_transaction.public_detail, serialized_logs)

        request_logs = [
            json.loads(line)
            for line in streams[1].getvalue().splitlines()
            if line
        ]
        self.assertIn("<transaction_id>", request_logs[-1]["path"])

    def test_openapi_documents_read_only_operations_endpoints(self):
        schema = self.client.get("/api/v1/openapi.json").json()

        transaction_query_path = next(
            path for path in schema["paths"] if path.endswith("/transactions")
        )
        ticket_query_path = next(
            path for path in schema["paths"] if path.endswith("/tickets")
        )
        transaction_path = next(
            path for path in schema["paths"] if "/transactions/" in path
        )
        ticket_path = next(path for path in schema["paths"] if "/tickets/" in path)
        self.assertEqual(set(schema["paths"][transaction_query_path]), {"get"})
        self.assertEqual(set(schema["paths"][ticket_query_path]), {"get"})
        self.assertEqual(set(schema["paths"][transaction_path]), {"get"})
        self.assertEqual(set(schema["paths"][ticket_path]), {"get"})

        transaction_parameters = schema["paths"][transaction_query_path]["get"][
            "parameters"
        ]
        self.assertNotIn(
            "workspace",
            {parameter["name"] for parameter in transaction_parameters},
        )
