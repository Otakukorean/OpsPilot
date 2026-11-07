"""URL configuration for the OpsPilot API project."""

from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import path

from .api import api


def healthcheck(request):
    """Return only service availability; never expose database error details."""

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", healthcheck, name="healthcheck"),
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls),
]
