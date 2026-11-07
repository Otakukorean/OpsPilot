import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import Membership, User, Workspace
from apps.operations.models import Ticket, Transaction


class SyntheticSeedCommandTests(TestCase):
    tester_environment = {
        "OPSPILOT_DEMO_PASSWORD": "synthetic-test-password",
        "OPSPILOT_TESTER_EMAIL": "tester@atlaspay.example",
        "OPSPILOT_TESTER_PASSWORD": "public-synthetic-tester-password",
    }

    @patch.dict(
        os.environ,
        tester_environment,
    )
    def test_seed_is_idempotent_and_creates_two_isolated_workspaces(self):
        output = StringIO()

        call_command("seed_synthetic_data", stdout=output)
        call_command("seed_synthetic_data", stdout=output)

        self.assertEqual(Workspace.objects.count(), 2)
        self.assertEqual(User.objects.count(), 7)
        self.assertEqual(Membership.objects.count(), 7)
        self.assertEqual(Transaction.objects.count(), 16)
        self.assertEqual(Ticket.objects.count(), 16)
        self.assertEqual(Transaction.objects.filter(code="TXN-10492").count(), 2)
        self.assertEqual(Ticket.objects.filter(code="TKT-2001").count(), 2)
        self.assertEqual(Transaction.objects.filter(code="TXN-10588").count(), 2)
        self.assertEqual(Ticket.objects.filter(code="TKT-2008").count(), 2)
        self.assertNotIn("synthetic-test-password", output.getvalue())
        self.assertNotIn("public-synthetic-tester-password", output.getvalue())

        tester = User.objects.get(email="tester@atlaspay.example")
        self.assertTrue(tester.check_password("public-synthetic-tester-password"))
        self.assertFalse(tester.is_staff)
        self.assertFalse(tester.is_superuser)
        membership = tester.memberships.get()
        self.assertEqual(membership.workspace.name, "AtlasPay Demo")
        self.assertEqual(membership.role, Membership.Role.ANALYST)

    @patch.dict(os.environ, tester_environment)
    def test_seed_removes_elevated_and_cross_workspace_tester_access(self):
        call_command("seed_synthetic_data", stdout=StringIO())
        tester = User.objects.get(email="tester@atlaspay.example")
        other_workspace = Workspace.objects.get(name="NorthstarPay Demo")
        tester.memberships.update(is_active=False)
        Membership.objects.create(
            user=tester,
            workspace=other_workspace,
            role=Membership.Role.ADMIN,
            is_active=True,
        )
        tester.is_staff = True
        tester.is_superuser = True
        tester.save(update_fields=["is_staff", "is_superuser"])

        call_command("seed_synthetic_data", stdout=StringIO())

        tester.refresh_from_db()
        self.assertFalse(tester.is_staff)
        self.assertFalse(tester.is_superuser)
        self.assertEqual(tester.memberships.filter(is_active=True).count(), 1)
        membership = tester.memberships.get(is_active=True)
        self.assertEqual(membership.workspace.name, "AtlasPay Demo")
        self.assertEqual(membership.role, Membership.Role.ANALYST)
