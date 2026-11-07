from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Document, DocumentChunk


@admin.register(Document)
class DocumentAdmin(ModelAdmin):
    list_display = ("title", "workspace", "visibility", "status", "created_at")
    list_filter = ("workspace", "visibility", "status", "content_type")
    search_fields = ("title", "original_filename", "workspace__name", "sha256")
    autocomplete_fields = ("workspace", "uploaded_by")
    list_select_related = ("workspace", "uploaded_by")
    readonly_fields = (
        "id",
        "sha256",
        "size_bytes",
        "page_count",
        "status",
        "failure_reason",
        "embedding_model",
        "created_at",
        "updated_at",
    )


@admin.register(DocumentChunk)
class DocumentChunkAdmin(ModelAdmin):
    list_display = ("document", "workspace", "page", "chunk_index", "created_at")
    list_filter = ("workspace", "created_at")
    search_fields = ("document__title",)
    autocomplete_fields = ("document", "workspace")
    list_select_related = ("document", "workspace")
    readonly_fields = (
        "id",
        "document",
        "workspace",
        "document_version",
        "page",
        "chunk_index",
        "text",
        "embedding",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
