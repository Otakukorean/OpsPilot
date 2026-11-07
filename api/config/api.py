from ninja import NinjaAPI
from ninja.errors import HttpError, ValidationError
from ninja.security import django_auth

from apps.accounts.api import accounts_router, auth_router
from apps.audit.api import audit_router
from apps.conversations.api import conversations_router
from apps.operations.api import operations_router
from apps.knowledge.api import knowledge_router


api = NinjaAPI(
    title="OpsPilot API",
    version="1.0.0",
    description=(
        "Secure API for the OpsPilot support and operations copilot. Authentication "
        "uses Django sessions and CSRF protection. Workspace identity and roles are "
        "always resolved by the backend."
    ),
    auth=django_auth,
    docs_url="/docs",
    openapi_url="/openapi.json",
    urls_namespace="api-v1",
)


def _request_id(request):
    return getattr(request, "request_id", "unavailable")


@api.exception_handler(HttpError)
def http_error_handler(request, exc):
    if exc.status_code == 401:
        code = "AUTHENTICATION_REQUIRED"
        message = "Authentication is required."
    elif exc.status_code == 403 and "CSRF" in exc.message.upper():
        code = "CSRF_FAILED"
        message = "CSRF verification failed."
    elif exc.status_code == 403:
        code = "FORBIDDEN"
        message = "You do not have permission to perform this operation."
    elif exc.status_code == 404:
        code = "NOT_FOUND"
        message = "Resource not found."
    elif exc.status_code == 429:
        code = "RATE_LIMITED"
        message = exc.message
    else:
        code = "REQUEST_ERROR"
        message = exc.message

    return api.create_response(
        request,
        {
            "code": code,
            "message": message,
            "request_id": _request_id(request),
        },
        status=exc.status_code,
    )


@api.exception_handler(ValidationError)
def validation_error_handler(request, exc):
    details = []
    for error in exc.errors:
        location = ".".join(str(part) for part in error.get("loc", ()))
        details.append(
            {
                "location": location,
                "message": error.get("msg", "Invalid value."),
                "type": error.get("type", "validation_error"),
            }
        )

    return api.create_response(
        request,
        {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "request_id": _request_id(request),
            "details": details,
        },
        status=422,
    )


api.add_router("/auth/", auth_router)
api.add_router("/", accounts_router)
api.add_router("/", operations_router)
api.add_router("/", conversations_router)
api.add_router("/", audit_router)
api.add_router("/", knowledge_router)
