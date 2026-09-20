import structlog
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from django.db.models.functions import Lower

from global_settings.utils import ff_is_enabled
from iam.models import User
from notifications.models import Notification
from notifications.registry import NOTIFICATION_REGISTRY

logger = structlog.getLogger(__name__)


def in_app_enabled(notification_type: str) -> bool:
    if not ff_is_enabled("notification_centre"):
        return False
    from notifications.channels import in_app_allowed

    return in_app_allowed(notification_type)


def _user_resolver(all_recipients):
    """Resolve every address the caller will use in one query, then hand back a
    per-item lookup. A sweep resolves the same owners for every object it walks."""
    # `User.email` is a CharField, so `email__in` is case-sensitive. Everything else
    # resolving an address does it case-insensitively -- including this feature's own
    # email leg (core/email_utils.py) -- and two rules in one feature is the bug.
    emails = {str(r).lower() for r in all_recipients if not isinstance(r, User)}
    by_email = {
        user.email.lower(): user
        for user in (
            User.objects.annotate(email_lower=Lower("email")).filter(
                email_lower__in=emails
            )
            if emails
            else ()
        )
        if not user.is_third_party
    }

    def resolve(recipients) -> list[User]:
        users = []
        for recipient in recipients:
            if isinstance(recipient, User):
                if not recipient.is_third_party:
                    users.append(recipient)
            elif (user := by_email.get(str(recipient).lower())) is not None:
                users.append(user)
        return users

    return resolve


def _as_users(recipients) -> list[User]:
    recipients = list(recipients)
    return _user_resolver(recipients)(recipients)


def notify(
    notification_type: str,
    recipients,
    target,
    context: dict | None = None,
) -> list[Notification]:
    """Write one inbox row per recipient for `target`, or update the one already
    there. In-app only; email keeps its own path (docs §7)."""
    return notify_many(notification_type, [(recipients, target, context)])


def notify_many(
    notification_type: str, items, *, renotify: bool = False
) -> list[Notification]:
    """`notify` over a whole sweep. `items` is an iterable of
    (recipients, target, context); the channel state and the address resolution are
    constant across it, so only the upsert is per row.

    `renotify` re-opens a row the recipient had already read. A condition sweep runs
    nightly and must not, or every deadline would nag daily -- but the days the
    condition *escalates* are news, and the caller is what knows them.
    """
    entry = NOTIFICATION_REGISTRY.get(notification_type)
    if entry is None:
        logger.error("Unknown notification type", type=notification_type)
        return []
    if not in_app_enabled(notification_type):
        return []

    items = [
        (list(recipients), target, context) for recipients, target, context in items
    ]
    resolve = _user_resolver({r for recipients, _, _ in items for r in recipients})

    # A re-fire bumps an event row back to unread; on a condition row `is_read` is the
    # latch that stops the nightly sweep re-opening what you have dealt with, except on
    # the days the caller calls escalation.
    bump_unread = entry["mode"] == "event" or renotify
    written = []

    for recipients, target, context in items:
        content_type = ContentType.objects.get_for_model(target)

        # Producers' context also carries email-only material the title never uses.
        declared = {
            key: str(value)
            for key, value in (context or {}).items()
            if key in entry["context"]
        }

        users = resolve(recipients)
        for user in users:
            defaults = {"context": declared, "recipient_count": len(users)}
            if bump_unread:
                defaults["is_read"] = False
                defaults["read_at"] = None
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
    """Delete rows of `notification_type` whose condition no longer holds. `keep` is
    every (recipient_id, object_id) pair the sweep just found still true.

    Deleting rather than stamping re-arms the type: the natural key is freed, so a
    recurrence creates a fresh unread row (§4). The caller must be authoritative for
    the whole type -- several sweeps share one type, and one of them calling this
    would delete the others' rows.
    """
    if NOTIFICATION_REGISTRY.get(notification_type, {}).get("mode") != "condition":
        logger.error("clear_stale on a non-condition type", type=notification_type)
        return 0
    if not in_app_enabled(notification_type):
        # notify_many wrote nothing, so the sweep hands over an empty `keep`. Without
        # this the first run after a type is switched off deletes its whole history --
        # an empty keep must keep meaning "nothing is true any more", not "no channel".
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
