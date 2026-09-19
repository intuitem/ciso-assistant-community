import structlog
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from iam.models import Folder, User
from notifications.models import Notification
from notifications.registry import NOTIFICATION_REGISTRY

logger = structlog.getLogger(__name__)


def in_app_enabled(notification_type: str) -> bool:
    """Whether this type writes inbox rows.

    The registry declares the supported channels and they are all on; an admin may
    narrow them, never widen them. The narrowing layer is enterprise-only and not
    built yet, so today this is the registry alone.
    """
    entry = NOTIFICATION_REGISTRY.get(notification_type)
    return bool(entry) and "in_app" in entry["channels"]


def _as_users(recipients) -> list[User]:
    """In-app notification needs a real internal User; anything else is email-only.

    Producers group by email address, so accept either and resolve. Third-party
    users are excluded by design for v1.
    """
    users, emails = [], []
    for recipient in recipients:
        (users if isinstance(recipient, User) else emails).append(recipient)
    if emails:
        users.extend(User.objects.filter(email__in=emails))
    return [u for u in users if not u.is_third_party]


def notify(
    notification_type: str,
    recipients,
    target,
    context: dict | None = None,
) -> list[Notification]:
    """
    Write one inbox row per recipient for `target`, or update the one already there.

    In-app only. Email keeps its own path: a producer calls its existing send
    alongside this, so nothing about the email channel has to change for a type to
    gain an inbox (docs/notification_center_shaping.md §7).

    Upsert is keyed on (recipient, type, target). A re-fire bumps an `event` row back
    to unread, because you have genuinely been assigned the thing again; it leaves a
    `condition` row alone, because `is_read` is the latch that stops a nightly sweep
    re-opening something you have dealt with.

    Returns the rows written, so a condition sweep can accumulate them into the `keep`
    set that clear_stale takes.
    """
    entry = NOTIFICATION_REGISTRY.get(notification_type)
    if entry is None:
        logger.error("Unknown notification type", type=notification_type)
        return []
    if not in_app_enabled(notification_type):
        return []

    folder = Folder.get_folder(target)
    if folder is None:
        # FolderMixin defaults to the root folder rather than raising, which would
        # quietly expose the row to every root-level role. Refuse instead.
        logger.error(
            "Notification target has no folder, skipping",
            type=notification_type,
            target=repr(target),
        )
        return []

    content_type = ContentType.objects.get_for_model(target)
    bump_unread = entry["mode"] == "event"
    written = []

    # Only the variables the registry declares for this type: the producers' context
    # dicts also carry email-only material (descriptions, URLs, formatted lists) that
    # the title never uses and the inbox should not store.
    declared = {
        key: str(value)
        for key, value in (context or {}).items()
        if key in entry["context"]
    }

    for user in _as_users(recipients):
        defaults = {"context": declared, "folder": folder}
        if bump_unread:
            defaults["is_read"] = False
        row, _ = Notification.objects.update_or_create(
            recipient=user,
            type=notification_type,
            content_type=content_type,
            object_id=target.pk,
            defaults=defaults,
        )
        written.append(row)

    return written


@transaction.atomic
def clear_stale(notification_type: str, keep) -> int:
    """
    Delete rows of `notification_type` whose condition no longer holds.

    `keep` is every (recipient_id, object_id) pair the sweep just found still true.
    Deleting rather than stamping is what re-arms the type: the natural key is freed,
    so a recurrence creates a fresh unread row (§4).

    The caller must be authoritative for the whole type. Several periodic tasks share
    one type today -- evidence_expiring_soon is fed by the in_month, in_week and
    tomorrow sweeps -- so this cannot be called from inside one of them without the
    others' rows being deleted. It takes the union.
    """
    if NOTIFICATION_REGISTRY.get(notification_type, {}).get("mode") != "condition":
        logger.error("clear_stale on a non-condition type", type=notification_type)
        return 0

    keep = {(str(r), str(o)) for r, o in keep}
    stale = [
        n.pk
        for n in Notification.objects.filter(type=notification_type).only(
            "recipient_id", "object_id"
        )
        if (str(n.recipient_id), str(n.object_id)) not in keep
    ]
    if not stale:
        return 0
    deleted, _ = Notification.objects.filter(pk__in=stale).delete()
    logger.info("Cleared stale notifications", type=notification_type, deleted=deleted)
    return deleted
