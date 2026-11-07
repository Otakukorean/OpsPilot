from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import Workspace
from apps.operations.models import Ticket, Transaction


class OperationsModelTests(TestCase):
    def setUp(self):
        self.atlas = Workspace.objects.create(name="Atlas Synthetic")
        self.northstar = Workspace.objects.create(name="Northstar Synthetic")

    def test_display_codes_may_overlap_between_workspaces(self):
        for workspace in (self.atlas, self.northstar):
            Transaction.objects.create(
                workspace=workspace,
                code="txn-overlap",
                status=Transaction.Status.PENDING,
                public_detail="Synthetic detail.",
            )
            Ticket.objects.create(
                workspace=workspace,
                code="tkt-overlap",
                status=Ticket.Status.OPEN,
                public_detail="Synthetic detail.",
            )

        self.assertEqual(Transaction.objects.filter(code="TXN-OVERLAP").count(), 2)
        self.assertEqual(Ticket.objects.filter(code="TKT-OVERLAP").count(), 2)

    def test_display_code_is_unique_within_workspace(self):
        Transaction.objects.create(
            workspace=self.atlas,
            code="TXN-ONE",
            status=Transaction.Status.PENDING,
            public_detail="Synthetic detail.",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Transaction.objects.create(
                workspace=self.atlas,
                code="TXN-ONE",
                status=Transaction.Status.FAILED,
                public_detail="Different synthetic detail.",
            )
