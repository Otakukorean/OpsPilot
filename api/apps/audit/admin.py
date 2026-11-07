from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(ModelAdmin):
    list_display = (
        "action",
        "outcome",
        "resource_type",
        "actor",
        "workspace",
        "created_at",
    )
    list_filter = ("outcome", "resource_type", "action", "workspace")
    search_fields = ("action", "request_id", "actor__email", "workspace__name")
    list_select_related = ("actor", "workspace")
    readonly_fields = (
        "id",
        "workspace",
        "actor",
        "action",
        "outcome",
        "resource_type",
        "reason",
        "request_id",
        "duration_ms",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD", "OPTIONS"}

    def has_delete_permission(self, request, obj=None):
        return False
