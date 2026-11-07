from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import AgentRun, ToolInvocation


class ToolInvocationInline(TabularInline):
    model = ToolInvocation
    extra = 0
    can_delete = False
    readonly_fields = ("tool_name", "outcome", "reason", "duration_ms", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AgentRun)
class AgentRunAdmin(ModelAdmin):
    list_display = ("id", "status", "model", "actor", "workspace", "created_at")
    list_filter = ("status", "model", "workspace", "created_at")
    search_fields = ("id", "actor__email", "thread__title")
    list_select_related = ("actor", "workspace", "thread")
    readonly_fields = (
        "id", "workspace", "actor", "thread", "user_message",
        "assistant_message", "status", "model", "llm_calls", "tool_calls",
        "input_tokens", "output_tokens", "duration_ms", "error_code",
        "created_at", "completed_at",
    )
    inlines = (ToolInvocationInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ToolInvocation)
class ToolInvocationAdmin(ModelAdmin):
    list_display = ("tool_name", "outcome", "run", "duration_ms", "created_at")
    list_filter = ("tool_name", "outcome", "created_at")
    readonly_fields = ("id", "run", "tool_name", "outcome", "reason", "duration_ms", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
