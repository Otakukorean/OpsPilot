import io
import json
import logging

from django.conf import settings
from django.test import Client, TestCase

from apps.accounts.models import Membership, User, Workspace
from config.logging import JsonFormatter


class AccountsAPITests(TestCase):
    csrf_url = "/api/v1/auth/csrf"
    login_url = "/api/v1/auth/login"
    logout_url = "/api/v1/auth/logout"
    me_url = "/api/v1/me"

    def test_health_check_is_public_and_database_aware(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            email="analyst@example.com",
            password="synthetic-test-password",
            first_name="Synthetic",
            last_name="Analyst",
        )
        self.workspace = Workspace.objects.create(name="Synthetic Workspace")
        Membership.objects.create(
            user=self.user,
            workspace=self.workspace,
            role=Membership.Role.ANALYST,
        )

    def _csrf_token(self):
        response = self.client.get(self.csrf_url)
        self.assertEqual(response.status_code, 200)
        return self.client.cookies[settings.CSRF_COOKIE_NAME].value

    def _login(self, *, email="analyst@example.com", password="synthetic-test-password"):
        token = self._csrf_token()
        return self.client.post(
            self.login_url,
            data=json.dumps({"email": email, "password": password}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

    def _capture_json_logs(self, logger_name, callback):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        logger = logging.getLogger(logger_name)
        original_level = logger.level
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        try:
            callback()
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)

        return [json.loads(line) for line in stream.getvalue().splitlines()]

    def test_login_creates_session_and_returns_server_resolved_membership(self):
        response = self._login(email="ANALYST@EXAMPLE.COM")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["email"], "analyst@example.com")
        self.assertEqual(payload["membership"]["role"], Membership.Role.ANALYST)
        self.assertEqual(
            payload["membership"]["workspace"]["id"],
            str(self.workspace.id),
        )
        self.assertNotIn("password", payload)
        self.assertIn(settings.SESSION_COOKIE_NAME, self.client.cookies)

    def test_login_requires_csrf_token(self):
        response = self.client.post(
            self.login_url,
            data=json.dumps(
                {
                    "email": "analyst@example.com",
                    "password": "synthetic-test-password",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "CSRF_FAILED")

    def test_login_rejects_invalid_credentials_without_account_details(self):
        response = self._login(password="incorrect-password")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "INVALID_CREDENTIALS")
        self.assertNotContains(response, "analyst@example.com", status_code=401)

    def test_failed_login_log_excludes_credentials_and_email(self):
        submitted_password = "never-log-this-password"
        logs = self._capture_json_logs(
            "opspilot.auth",
            lambda: self._login(password=submitted_password),
        )

        failure = next(log for log in logs if log["event"] == "auth.login.failure")
        serialized_logs = json.dumps(logs)
        self.assertEqual(failure["outcome"], "denied")
        self.assertEqual(failure["reason"], "invalid_credentials")
        self.assertNotIn(submitted_password, serialized_logs)
        self.assertNotIn(self.user.email, serialized_logs)

    def test_successful_login_log_uses_internal_identity(self):
        logs = self._capture_json_logs("opspilot.auth", self._login)

        success = next(log for log in logs if log["event"] == "auth.login.success")
        self.assertEqual(success["user_id"], str(self.user.id))
        self.assertEqual(success["workspace_id"], str(self.workspace.id))
        self.assertEqual(success["role"], Membership.Role.ANALYST)
        self.assertEqual(success["outcome"], "allowed")

    def test_me_requires_authentication(self):
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "AUTHENTICATION_REQUIRED")
        self.assertEqual(response.json()["request_id"], response["X-Request-ID"])

    def test_request_log_contains_correlation_and_timing_metadata(self):
        responses = []
        logs = self._capture_json_logs(
            "opspilot.request",
            lambda: responses.append(self.client.get(self.me_url)),
        )

        request_log = next(
            log for log in logs if log["event"] == "http.request.completed"
        )
        self.assertEqual(request_log["request_id"], responses[0]["X-Request-ID"])
        self.assertEqual(request_log["method"], "GET")
        self.assertEqual(request_log["path"], self.me_url)
        self.assertEqual(request_log["status_code"], 401)
        self.assertGreaterEqual(request_log["duration_ms"], 0)

    def test_me_returns_authenticated_user_context(self):
        self.assertEqual(self._login().status_code, 200)

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], self.user.email)

    def test_logout_requires_csrf_and_invalidates_session(self):
        self.assertEqual(self._login().status_code, 200)

        missing_csrf_response = self.client.post(self.logout_url)
        self.assertEqual(missing_csrf_response.status_code, 403)

        token = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        response = self.client.post(
            self.logout_url,
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get(self.me_url).status_code, 401)

    def test_validation_error_does_not_echo_password(self):
        token = self._csrf_token()
        response = self.client.post(
            self.login_url,
            data=json.dumps({"password": "never-echo-this-password"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "VALIDATION_ERROR")
        self.assertNotContains(
            response,
            "never-echo-this-password",
            status_code=422,
        )

    def test_swagger_and_openapi_document_account_operations(self):
        docs_response = self.client.get("/api/v1/docs")
        schema_response = self.client.get("/api/v1/openapi.json")

        self.assertEqual(docs_response.status_code, 200)
        self.assertEqual(schema_response.status_code, 200)

        schema = schema_response.json()
        paths = schema["paths"]
        self.assertTrue(any(path.endswith("/auth/login") for path in paths))
        self.assertTrue(any(path.endswith("/auth/logout") for path in paths))
        self.assertTrue(any(path.endswith("/me") for path in paths))
        self.assertTrue(schema["components"]["securitySchemes"])
