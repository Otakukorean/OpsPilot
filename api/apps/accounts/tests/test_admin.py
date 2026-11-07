from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


class AccountsAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="synthetic-test-password",
        )
        self.client.force_login(self.admin_user)

    def test_accounts_admin_pages_are_available(self):
        admin_urls = (
            "admin:accounts_user_changelist",
            "admin:accounts_workspace_changelist",
            "admin:accounts_membership_changelist",
            "admin:auth_group_changelist",
        )

        for url_name in admin_urls:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)

    def test_user_add_page_uses_email_without_username(self):
        response = self.client.get(reverse("admin:accounts_user_add"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="email"')
        self.assertNotContains(response, 'name="username"')
