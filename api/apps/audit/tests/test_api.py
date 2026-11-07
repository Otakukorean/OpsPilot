import json

from django.test import Client, TestCase

from apps.accounts.models import Membership, User, Workspace
from apps.audit.models import AuditEvent
from apps.operations.models import Transaction


class AuditAPITests(TestCase):
    audit_url = "/api/v1/admin/audit"

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.atlas = Workspace.objects.create(name="Atlas Audit")
        self.northstar = Workspace.objects.create(name="Northstar Audit")
        self.admin = self._create_user(
            "admin@atlas-audit.example",
            self.atlas,
            Membership.Role.ADMIN,
        )
        self.analyst = self._create_user(
            "analyst@atlas-audit.example",
            self.atlas,
            Membership.Role.ANALYST,
        )
        self.viewer = self._create_user(
            "viewer@atlas-audit.example",
            self.atlas,
            Membership.Role.VIEWER,
        )
        self.foreign_admin = self._create_user(
            "admin@northstar-audit.example",
            self.northstar,
            Membership.Role.ADMIN,
        )
        self.atlas_event = AuditEvent.objects.create(
            workspace=self.atlas,
            actor=self.analyst,
            action="operations.transaction.read",
            outcome=AuditEvent.Outcome.ALLOWED,
            resource_type="transaction",
            request_id="11111111-1111-1111-1111-111111111111",
        )
        self.foreign_event = AuditEvent.objects.create(
            workspace=self.northstar,
            actor=self.foreign_admin,
            action="operations.transaction.read",
            outcome=AuditEvent.Outcome.DENIED,
            resource_type="transaction",
            reason="not_found_in_workspace",
            request_id="22222222-2222-2222-2222-222222222222",
        )

    def _create_user(self, email, workspace, role):
        user = User.objects.create_user(email=email, password="synthetic-password")
        Membership.objects.create(user=user, workspace=workspace, role=role)
        return user

    def test_audit_endpoint_requires_authentication(self):
        response = self.client.get(self.audit_url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "AUTHENTICATION_REQUIRED")

    def test_only_workspace_admin_can_read_audit_events(self):
        for user in (self.analyst, self.viewer):
            self.client.force_login(user)
            with self.subTest(role=user.memberships.get().role):
                response = self.client.get(self.audit_url)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["code"], "FORBIDDEN")
                self.assertTrue(
                    AuditEvent.objects.filter(
                        actor=user,
                        workspace=self.atlas,
                        action="audit.list",
                        outcome=AuditEvent.Outcome.DENIED,
                        reason="admin_role_required",
                    ).exists()
                )

    def test_admin_reads_only_active_workspace_audit_metadata(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.audit_url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        serialized = json.dumps(payload)
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["id"], str(self.atlas_event.id))
        self.assertNotIn(str(self.foreign_event.id), serialized)
        self.assertNotIn(str(self.northstar.id), serialized)
        self.assertNotIn("workspace", payload["items"][0])

    def test_audit_filters_and_pagination_are_bounded(self):
        AuditEvent.objects.create(
            workspace=self.atlas,
            actor=self.analyst,
            action="conversations.thread.read",
            outcome=AuditEvent.Outcome.DENIED,
            resource_type="thread",
            reason="not_found_for_owner",
            request_id="33333333-3333-3333-3333-333333333333",
        )
        self.client.force_login(self.admin)

        filtered = self.client.get(
            self.audit_url,
            {
                "action": "conversations.thread.read",
                "outcome": "denied",
                "resource_type": "thread",
                "limit": 1,
                "offset": 0,
            },
        )
        oversized = self.client.get(self.audit_url, {"limit": 51})

        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.json()["total"], 1)
        self.assertEqual(len(filtered.json()["items"]), 1)
        self.assertEqual(oversized.status_code, 422)

    def test_operations_access_creates_metadata_only_audit_event(self):
        transaction = Transaction.objects.create(
            workspace=self.atlas,
            code="TXN-AUDIT",
            status=Transaction.Status.COMPLETED,
            public_detail="Never copy this synthetic detail into audit metadata.",
        )
        self.client.force_login(self.analyst)

        response = self.client.get(f"/api/v1/transactions/{transaction.id}")

        self.assertEqual(response.status_code, 200)
        event = AuditEvent.objects.filter(
            actor=self.analyst,
            action="operations.transaction.read",
            outcome=AuditEvent.Outcome.ALLOWED,
        ).latest("created_at")
        serialized_event = " ".join(
            (
                event.action,
                event.resource_type,
                event.reason,
                event.request_id,
            )
        )
        self.assertNotIn(transaction.public_detail, serialized_event)
        self.assertFalse(hasattr(event, "payload"))
        self.assertFalse(hasattr(event, "body"))

    def test_openapi_audit_query_has_no_workspace_parameter(self):
        schema = self.client.get("/api/v1/openapi.json").json()
        path = next(path for path in schema["paths"] if path.endswith("/admin/audit"))
        parameters = schema["paths"][path]["get"]["parameters"]

        self.assertNotIn(
            "workspace",
            {parameter["name"] for parameter in parameters},
        )
