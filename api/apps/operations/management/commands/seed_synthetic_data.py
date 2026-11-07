import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Membership, User, Workspace
from apps.operations.models import Ticket, Transaction


WORKSPACES = (
    {
        "name": "AtlasPay Demo",
        "slug": "atlaspay",
        "transactions": (
            (
                "TXN-10492",
                Transaction.Status.FAILED,
                "Duplicate synthetic request rejected with demo code T24-000.",
            ),
            (
                "TXN-10501",
                Transaction.Status.COMPLETED,
                "Synthetic payment completed in the demo environment.",
            ),
            (
                "TXN-10515",
                Transaction.Status.PENDING,
                "Synthetic transfer is awaiting a scheduled risk-simulator review.",
            ),
            (
                "TXN-10528",
                Transaction.Status.FAILED,
                "Synthetic merchant reference failed validation with demo code SYN-VAL-12.",
            ),
            (
                "TXN-10544",
                Transaction.Status.COMPLETED,
                "Synthetic batch settlement completed and received a demo confirmation.",
            ),
            (
                "TXN-10563",
                Transaction.Status.PENDING,
                "Synthetic payout is queued for the next demo settlement window.",
            ),
            (
                "TXN-10579",
                Transaction.Status.FAILED,
                "Duplicate synthetic idempotency key rejected with demo code DUP-409.",
            ),
            (
                "TXN-10588",
                Transaction.Status.COMPLETED,
                "Synthetic payout completed after sandbox reconciliation.",
            ),
        ),
        "tickets": (
            (
                "TKT-2001",
                Ticket.Status.IN_PROGRESS,
                "Synthetic analyst is reviewing a duplicate request report.",
            ),
            (
                "TKT-2002",
                Ticket.Status.RESOLVED,
                "Synthetic status notification issue was resolved.",
            ),
            (
                "TKT-2003",
                Ticket.Status.OPEN,
                "Synthetic merchant reported a reference-validation failure for TXN-10528.",
            ),
            (
                "TKT-2004",
                Ticket.Status.IN_PROGRESS,
                "Synthetic operations team is reviewing the pending settlement window.",
            ),
            (
                "TKT-2005",
                Ticket.Status.RESOLVED,
                "Synthetic batch confirmation was verified against the demo ledger.",
            ),
            (
                "TKT-2006",
                Ticket.Status.OPEN,
                "Synthetic duplicate idempotency report requires analyst triage.",
            ),
            (
                "TKT-2007",
                Ticket.Status.IN_PROGRESS,
                "Synthetic payout timing question is under review.",
            ),
            (
                "TKT-2008",
                Ticket.Status.RESOLVED,
                "Synthetic reconciliation discrepancy was closed after verification.",
            ),
        ),
    },
    {
        "name": "NorthstarPay Demo",
        "slug": "northstarpay",
        "transactions": (
            (
                "TXN-10492",
                Transaction.Status.COMPLETED,
                "Separate synthetic transaction completed successfully.",
            ),
            (
                "TXN-10501",
                Transaction.Status.PENDING,
                "Synthetic transaction is awaiting demo settlement.",
            ),
            (
                "TXN-10515",
                Transaction.Status.COMPLETED,
                "Separate synthetic transfer completed after sandbox review.",
            ),
            (
                "TXN-10528",
                Transaction.Status.PENDING,
                "Separate synthetic transaction is waiting for a demo merchant response.",
            ),
            (
                "TXN-10544",
                Transaction.Status.FAILED,
                "Synthetic beneficiary route was unavailable with demo code NET-101.",
            ),
            (
                "TXN-10563",
                Transaction.Status.COMPLETED,
                "Separate synthetic payout completed in the current settlement window.",
            ),
            (
                "TXN-10579",
                Transaction.Status.PENDING,
                "Synthetic transfer is queued for sandbox reconciliation.",
            ),
            (
                "TXN-10588",
                Transaction.Status.FAILED,
                "Synthetic account token expired with demo code TOK-401.",
            ),
        ),
        "tickets": (
            (
                "TKT-2001",
                Ticket.Status.OPEN,
                "Separate synthetic ticket awaiting analyst review.",
            ),
            (
                "TKT-2002",
                Ticket.Status.RESOLVED,
                "Synthetic reconciliation question was resolved.",
            ),
            (
                "TKT-2003",
                Ticket.Status.IN_PROGRESS,
                "Separate synthetic merchant response is being monitored.",
            ),
            (
                "TKT-2004",
                Ticket.Status.OPEN,
                "Synthetic beneficiary-route failure for TXN-10544 awaits triage.",
            ),
            (
                "TKT-2005",
                Ticket.Status.RESOLVED,
                "Synthetic settlement confirmation was delivered successfully.",
            ),
            (
                "TKT-2006",
                Ticket.Status.IN_PROGRESS,
                "Synthetic reconciliation queue is being reviewed by an analyst.",
            ),
            (
                "TKT-2007",
                Ticket.Status.OPEN,
                "Synthetic expired-token failure for TXN-10588 needs investigation.",
            ),
            (
                "TKT-2008",
                Ticket.Status.RESOLVED,
                "Synthetic merchant callback issue was closed in the demo environment.",
            ),
        ),
    },
)


class Command(BaseCommand):
    help = "Create idempotent fictional P0 workspaces, users, tickets, and transactions."

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get("OPSPILOT_DEMO_PASSWORD")
        if not password:
            raise CommandError("Set OPSPILOT_DEMO_PASSWORD before seeding demo users.")

        tester_email = os.environ.get(
            "OPSPILOT_TESTER_EMAIL", "tester@atlaspay.example"
        ).strip().casefold()
        tester_password = os.environ.get(
            "OPSPILOT_TESTER_PASSWORD", "OpsPilot-Demo-2026!"
        )
        reserved_emails = {
            f"{role}@{workspace['slug']}.example"
            for workspace in WORKSPACES
            for role in (
                Membership.Role.ADMIN,
                Membership.Role.ANALYST,
                Membership.Role.VIEWER,
            )
        }
        if not tester_email or len(tester_password) < 12:
            raise CommandError("Set valid OpsPilot tester credentials before seeding.")
        if tester_email in reserved_emails:
            raise CommandError("The tester email must not match a role-based demo user.")

        for workspace_data in WORKSPACES:
            workspace, _ = Workspace.objects.get_or_create(
                name=workspace_data["name"]
            )
            self._seed_users(workspace, workspace_data["slug"], password)
            if workspace_data["slug"] == "atlaspay":
                self._seed_tester(workspace, tester_email, tester_password)
            self._seed_transactions(workspace, workspace_data["transactions"])
            self._seed_tickets(workspace, workspace_data["tickets"])

        self.stdout.write(
            self.style.SUCCESS(
                "Synthetic seed complete: 2 workspaces, 7 users, "
                f"{sum(len(item['transactions']) for item in WORKSPACES)} "
                "transactions, and "
                f"{sum(len(item['tickets']) for item in WORKSPACES)} tickets."
            )
        )

    def _seed_users(self, workspace, slug, password):
        for role in (
            Membership.Role.ADMIN,
            Membership.Role.ANALYST,
            Membership.Role.VIEWER,
        ):
            email = f"{role}@{slug}.example"
            user, _ = User.objects.update_or_create(
                email=email,
                defaults={
                    "first_name": "Synthetic",
                    "last_name": role.title(),
                    "is_active": True,
                },
            )
            user.set_password(password)
            user.save(update_fields=["password"])
            Membership.objects.update_or_create(
                user=user,
                workspace=workspace,
                defaults={"role": role, "is_active": True},
            )

    def _seed_tester(self, workspace, email, password):
        user, _ = User.objects.update_or_create(
            email=email,
            defaults={
                "first_name": "Portfolio",
                "last_name": "Tester",
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        user.set_password(password)
        user.save(update_fields=["password"])
        Membership.objects.filter(user=user).exclude(workspace=workspace).update(
            is_active=False
        )
        Membership.objects.update_or_create(
            user=user,
            workspace=workspace,
            defaults={"role": Membership.Role.ANALYST, "is_active": True},
        )

    def _seed_transactions(self, workspace, records):
        for code, status, public_detail in records:
            Transaction.objects.update_or_create(
                workspace=workspace,
                code=code,
                defaults={"status": status, "public_detail": public_detail},
            )

    def _seed_tickets(self, workspace, records):
        for code, status, public_detail in records:
            Ticket.objects.update_or_create(
                workspace=workspace,
                code=code,
                defaults={"status": status, "public_detail": public_detail},
            )
