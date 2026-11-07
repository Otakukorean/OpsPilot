from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm

from .forms import UserChangeForm, UserCreationForm
from .models import Membership, User, Workspace


class MembershipInline(TabularInline):
    model = Membership
    extra = 0
    fields = ("workspace", "role", "is_active", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("workspace",)
    show_change_link = True


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    filter_horizontal = ("groups", "user_permissions")
    inlines = (MembershipInline,)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal information"), {"fields": ("first_name", "last_name")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )


@admin.register(Workspace)
class WorkspaceAdmin(ModelAdmin):
    list_display = ("name", "id", "created_at")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at")
    inlines = (MembershipInline,)


@admin.register(Membership)
class MembershipAdmin(ModelAdmin):
    list_display = ("user", "workspace", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "workspace")
    search_fields = ("user__email", "workspace__name")
    autocomplete_fields = ("user", "workspace")
    list_select_related = ("user", "workspace")
    readonly_fields = ("id", "created_at")


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
