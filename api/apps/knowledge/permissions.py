from django.core.exceptions import PermissionDenied

from apps.accounts.models import Membership


VISIBILITY_BY_ROLE = {
    Membership.Role.ADMIN: {
        "admin",
        "analyst",
        "viewer",
    },
    Membership.Role.ANALYST: {
        "analyst",
        "viewer",
    },
    Membership.Role.VIEWER: {"viewer"},
}


def resolve_knowledge_membership(user):
    membership = (
        user.memberships.filter(is_active=True)
        .select_related("workspace")
        .first()
    )
    if membership is None or membership.role not in VISIBILITY_BY_ROLE:
        raise PermissionDenied
    return membership


def require_admin_membership(user):
    membership = resolve_knowledge_membership(user)
    if membership.role != Membership.Role.ADMIN:
        raise PermissionDenied
    return membership


def permitted_visibilities(role):
    return VISIBILITY_BY_ROLE.get(role, set())
