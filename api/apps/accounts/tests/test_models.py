from uuid import UUID

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import Membership, User, Workspace


class UserModelTests(TestCase):
    def test_create_user_uses_normalized_email_and_hashed_password(self):
        user = User.objects.create_user(
            email="Analyst@Example.COM",
            password="synthetic-test-password",
        )

        self.assertIsInstance(user.id, UUID)
        self.assertEqual(user.email, "analyst@example.com")
        self.assertTrue(user.check_password("synthetic-test-password"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_email_is_unique_case_insensitively(self):
        User.objects.create_user(
            email="analyst@example.com",
            password="synthetic-test-password",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                email="ANALYST@EXAMPLE.COM",
                password="another-synthetic-test-password",
            )

    def test_create_superuser_sets_required_flags(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="synthetic-test-password",
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class MembershipModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="viewer@example.com",
            password="synthetic-test-password",
        )
        self.first_workspace = Workspace.objects.create(name="Synthetic Workspace One")
        self.second_workspace = Workspace.objects.create(name="Synthetic Workspace Two")

    def test_user_can_have_only_one_active_membership(self):
        Membership.objects.create(
            user=self.user,
            workspace=self.first_workspace,
            role=Membership.Role.VIEWER,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Membership.objects.create(
                user=self.user,
                workspace=self.second_workspace,
                role=Membership.Role.ANALYST,
            )

    def test_inactive_historical_membership_is_allowed(self):
        Membership.objects.create(
            user=self.user,
            workspace=self.first_workspace,
            role=Membership.Role.VIEWER,
        )

        historical_membership = Membership.objects.create(
            user=self.user,
            workspace=self.second_workspace,
            role=Membership.Role.ANALYST,
            is_active=False,
        )

        self.assertFalse(historical_membership.is_active)
