import logging
import time
import uuid

from django.utils.deprecation import MiddlewareMixin


request_logger = logging.getLogger("opspilot.request")


class RequestIDMiddleware(MiddlewareMixin):
    """Attach a server-generated correlation ID to every request and response."""

    def process_request(self, request):
        request.request_id = str(uuid.uuid4())
        request.request_started_at = time.monotonic()

    def process_response(self, request, response):
        request_id = getattr(request, "request_id", None)
        if request_id:
            response["X-Request-ID"] = request_id

        started_at = getattr(request, "request_started_at", None)
        duration_ms = None
        if started_at is not None:
            duration_ms = round((time.monotonic() - started_at) * 1000, 2)

        user = getattr(request, "user", None)
        user_id = None
        if user is not None and user.is_authenticated:
            user_id = str(user.pk)

        status_code = response.status_code
        route = getattr(getattr(request, "resolver_match", None), "route", None)
        safe_path = f"/{route}" if route else request.path
        level = logging.INFO
        if status_code >= 500:
            level = logging.ERROR
        elif status_code >= 400:
            level = logging.WARNING

        request_logger.log(
            level,
            "HTTP request completed",
            extra={
                "event": "http.request.completed",
                "request_id": request_id,
                "method": request.method,
                "path": safe_path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "user_id": user_id,
            },
        )
        return response
