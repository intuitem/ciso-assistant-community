from datetime import datetime, timedelta

import structlog
from django.conf import settings
from django.contrib.auth.models import Permission
from django.db.models import Q

from iam.models import RoleAssignment, User

logger = structlog.get_logger(__name__)

# A license stays valid through the end of its expiration day, so a one-day
# grace period is added to the configured expiration date. Single source of
# truth shared by license enforcement (permissions) and status reporting (views).
LICENSE_GRACE_PERIOD = timedelta(days=1)

# Permissions that grant write access but do not consume a license seat
NON_SEAT_PERMISSIONS = {
    "change_validationflow",
    "add_chatsession",
    "change_chatsession",
    "delete_chatsession",
    "change_notification",
    "delete_notification",
}


def effective_expiration(expiration_date: datetime) -> datetime:
    """Return the moment the license actually stops being valid."""
    return expiration_date + LICENSE_GRACE_PERIOD


def is_editor(user: User) -> bool:
    permissions = RoleAssignment.get_permissions(user)
    editor_prefixes = {"add_", "change_", "delete_"}
    return any(
        any(perm.startswith(prefix) for prefix in editor_prefixes)
        for perm in permissions
        if perm not in NON_SEAT_PERMISSIONS
    )


def get_editors() -> list[User]:
    editor_permissions = Permission.objects.filter(
        Q(codename__startswith="add_")
        | Q(codename__startswith="change_")
        | Q(codename__startswith="delete_")
    ).exclude(codename__in=NON_SEAT_PERMISSIONS)
    return list(
        RoleAssignment.users_with_permission_anywhere(editor_permissions)
        .exclude(service_account__isnull=False)
        .filter(is_third_party=False)
    )


def seat_limit_reachable(seats: int) -> bool:
    """Whether the editor count could reach `seats`.

    Editors are drawn from these users only (same filters as get_editors), so
    while they number fewer than `seats` no seat check can fail and its per-user
    scan can be skipped. Unlimited licenses are issued with more seats than
    users: for them every seat check costs this one COUNT."""
    return (
        User.objects.exclude(service_account__isnull=False)
        .filter(is_third_party=False)
        .count()
        >= seats
    )


def check_restored_seats() -> str | None:
    """Backup restore validator (settings.BACKUP_RESTORE_VALIDATORS): a restored
    backup may not hold more editors than the license allows."""
    seats = settings.LICENSE_SEATS
    if not seat_limit_reachable(seats):
        return None
    editor_count = len(get_editors())
    if editor_count > seats:
        logger.error(
            "Backup exceeds license seats",
            editor_count=editor_count,
            license_seats=seats,
        )
        return "errorLicenseSeatsExceeded"
    return None
