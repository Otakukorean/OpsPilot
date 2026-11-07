from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Ticket, Transaction


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ("code", "workspace", "status", "created_at")
    list_filter = ("status", "workspace")
    search_fields = ("code", "public_detail", "workspace__name")
    autocomplete_fields = ("workspace",)
    list_select_related = ("workspace",)
    readonly_fields = ("id", "created_at")


@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    list_display = ("code", "workspace", "status", "created_at")
    list_filter = ("status", "workspace")
    search_fields = ("code", "public_detail", "workspace__name")
    autocomplete_fields = ("workspace",)
    list_select_related = ("workspace",)
    readonly_fields = ("id", "created_at")
