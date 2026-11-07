from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import ChatMessage, ChatThread, MessageCitation


class ChatMessageInline(TabularInline):
    model = ChatMessage
    extra = 0
    fields = ("role", "status", "created_at")
    readonly_fields = ("role", "status", "created_at")
    show_change_link = True


@admin.register(ChatThread)
class ChatThreadAdmin(ModelAdmin):
    list_display = ("title", "owner", "workspace", "updated_at")
    list_filter = ("workspace", "created_at", "updated_at")
    search_fields = ("title", "owner__email", "workspace__name")
    autocomplete_fields = ("owner", "workspace")
    list_select_related = ("owner", "workspace")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (ChatMessageInline,)


@admin.register(ChatMessage)
class ChatMessageAdmin(ModelAdmin):
    list_display = ("thread", "role", "status", "created_at")
    list_filter = ("role", "status", "created_at")
    search_fields = ("thread__title", "thread__owner__email")
    autocomplete_fields = ("thread",)
    list_select_related = ("thread",)
    readonly_fields = ("id", "created_at")


@admin.register(MessageCitation)
class MessageCitationAdmin(ModelAdmin):
    list_display = ("message", "source_number", "title", "page")
    search_fields = ("title", "message__thread__title")
    readonly_fields = (
        "id", "message", "document", "chunk", "source_number", "title", "page", "excerpt"
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
