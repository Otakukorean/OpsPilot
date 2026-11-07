from django.core.exceptions import PermissionDenied

from apps.accounts.models import Membership


OPERATIONS_READ_ROLES = {
    Membership.Role.ADMIN,
    Membership.Role.ANALYST,
}


def resolve_operations_membership(user):
    """Return the server-derived membership allowed to read operations data."""

    membership = (
        user.memberships.filter(is_active=True)
        .select_related("workspace")
        .first()
    )
    if membership is None or membership.role not in OPERATIONS_READ_ROLES:
        raise PermissionDenied
    return membership
