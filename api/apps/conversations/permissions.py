from django.core.exceptions import PermissionDenied


def resolve_active_membership(user):
    """Resolve the active workspace exclusively from authenticated server state."""

    membership = (
        user.memberships.filter(is_active=True)
        .select_related("workspace")
        .first()
    )
    if membership is None:
        raise PermissionDenied
    return membership
