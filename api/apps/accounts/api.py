import logging

from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from ninja import Router
from ninja.errors import HttpError
from ninja.utils import check_csrf

from .models import User
from .schemas import (
    ErrorOut,
    LoginIn,
    MessageOut,
    UserContextOut,
    ValidationErrorOut,
)


audit_logger = logging.getLogger("opspilot.auth")
auth_router = Router(tags=["Authentication"])
accounts_router = Router(tags=["Accounts"])


def _error(request, *, code, message):
    return {
        "code": code,
        "message": message,
        "request_id": request.request_id,
    }


def _user_context(user):
    membership = (
        user.memberships.filter(is_active=True)
        .select_related("workspace")
        .first()
    )

    membership_data = None
    if membership:
        membership_data = {
            "workspace": {
                "id": membership.workspace_id,
                "name": membership.workspace.name,
            },
            "role": membership.role,
        }

    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "membership": membership_data,
    }


def csrf_auth(request):
    """Require Django's CSRF token without requiring an authenticated session."""

    error_response = check_csrf(request)
    if error_response:
        audit_logger.warning(
            "Authentication CSRF verification failed",
            extra={
                "event": "auth.csrf.failure",
                "request_id": request.request_id,
                "path": request.path,
                "outcome": "denied",
            },
        )
        raise HttpError(403, "CSRF verification failed.")
    return True


@auth_router.get(
    "/csrf",
    auth=None,
    response={200: MessageOut},
    operation_id="getCsrfCookie",
    summary="Initialize CSRF protection",
    description=(
        "Sets Django's CSRF cookie. Browser clients must send its value in the "
        "X-CSRFToken header for login, logout, and future unsafe requests."
    ),
)
@ensure_csrf_cookie
@csrf_exempt
def get_csrf_cookie(request):
    return JsonResponse({"message": "CSRF cookie initialized."})


@auth_router.post(
    "/login",
    auth=csrf_auth,
    response={
        200: UserContextOut,
        401: ErrorOut,
        403: ErrorOut,
        422: ValidationErrorOut,
    },
    operation_id="login",
    summary="Sign in with email and password",
    description=(
        "Creates a database-backed Django session. Call the CSRF endpoint first "
        "and include the X-CSRFToken header. Invalid credentials always return a "
        "generic response to avoid account enumeration."
    ),
)
def login(request, payload: LoginIn):
    normalized_email = User.objects.normalize_email(payload.email).casefold()
    user = authenticate(
        request,
        username=normalized_email,
        password=payload.password.get_secret_value(),
    )

    if user is None:
        audit_logger.warning(
            "Login failed",
            extra={
                "event": "auth.login.failure",
                "request_id": request.request_id,
                "outcome": "denied",
                "reason": "invalid_credentials",
            },
        )
        return 401, _error(
            request,
            code="INVALID_CREDENTIALS",
            message="The email or password is incorrect.",
        )

    django_login(request, user)
    context = _user_context(user)
    membership = context["membership"]
    audit_logger.info(
        "Login succeeded",
        extra={
            "event": "auth.login.success",
            "request_id": request.request_id,
            "user_id": str(user.pk),
            "workspace_id": (
                str(membership["workspace"]["id"]) if membership else None
            ),
            "role": membership["role"] if membership else None,
            "outcome": "allowed",
        },
    )
    return context


@auth_router.post(
    "/logout",
    response={
        204: None,
        401: ErrorOut,
        403: ErrorOut,
    },
    operation_id="logout",
    summary="End the current session",
    description="Deletes the current server-side session and clears its cookie.",
)
def logout(request):
    user_id = str(request.auth.pk)
    django_logout(request)
    audit_logger.info(
        "Logout succeeded",
        extra={
            "event": "auth.logout.success",
            "request_id": request.request_id,
            "user_id": user_id,
            "outcome": "allowed",
        },
    )
    return 204, None


@accounts_router.get(
    "/me",
    response={
        200: UserContextOut,
        401: ErrorOut,
    },
    operation_id="getCurrentUser",
    summary="Get the authenticated user context",
    description=(
        "Returns the authenticated user and active workspace membership resolved "
        "entirely from server-side state. No client-supplied workspace is accepted."
    ),
)
def me(request):
    return _user_context(request.auth)
