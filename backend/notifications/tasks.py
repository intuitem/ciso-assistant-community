from datetime import timedelta

import structlog
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import db_periodic_task

from notifications.models import Notification

logger = structlog.getLogger(__name__)

# Backstop: condition rows mostly leave via clear_stale, so this is what removes the
# event types. Mirrors AUDITLOG_RETENTION_DAYS.
RETENTION_DAYS = 90

# Ceiling on one inbox. Past this, something upstream is wrong.
MAX_PER_RECIPIENT = 1000


def prune_read_notifications() -> int:
    """Delete read rows past the retention window."""
    cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
    deleted, _ = Notification.objects.filter(
        is_read=True, updated_at__lt=cutoff
    ).delete()
    return deleted


def enforce_per_recipient_cap() -> int:
    """Keep the most useful MAX_PER_RECIPIENT rows per recipient.

    Ordered unread-first, then newest-first, so the surplus taken off the tail is read
    history before it is anything else. Unread rows are still capped -- a filter that
    spared them would make the ceiling soft in the one case it exists for, since a
    runaway producer writes unread.
    """
    over_cap = (
        Notification.objects.values("recipient")
        .annotate(total=Count("id"))
        .filter(total__gt=MAX_PER_RECIPIENT)
    )
    deleted = 0
    for row in over_cap:
        surplus = list(
            Notification.objects.filter(recipient=row["recipient"])
            .order_by("is_read", "-created_at")
            .values_list("id", flat=True)[MAX_PER_RECIPIENT:]
        )
        if surplus:
            count, _ = Notification.objects.filter(id__in=surplus).delete()
            deleted += count
    return deleted


def prune_orphaned_notifications() -> int:
    """Delete rows whose target no longer exists: a GenericForeignKey has no database
    cascade.

    A nightly sweep rather than a `post_delete` receiver, which would run on every
    delete in the product. Click-to-open already degrades safely on an orphan.
    """
    deleted = 0
    for content_type_id in Notification.objects.values_list(
        "content_type", flat=True
    ).distinct():
        content_type = ContentType.objects.get_for_id(content_type_id)
        model = content_type.model_class()
        targets = set(
            Notification.objects.filter(content_type=content_type)
            .values_list("object_id", flat=True)
            .distinct()
        )
        if model is None:
            # The model itself is gone (an app removed between releases).
            stale = targets
        else:
            alive = set(
                model.objects.filter(pk__in=targets).values_list("pk", flat=True)
            )
            stale = targets - alive
        if stale:
            count, _ = Notification.objects.filter(
                content_type=content_type, object_id__in=stale
            ).delete()
            deleted += count
    return deleted


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="3", minute="30"))
def notification_housekeeping():
    """Retention, cap and orphans in one nightly pass: same table, one write window.
    Each step is a plain function so it can be tested without Huey."""
    try:
        expired = prune_read_notifications()
        capped = enforce_per_recipient_cap()
        orphaned = prune_orphaned_notifications()
    except Exception:
        logger.error("Notification housekeeping failed", exc_info=True)
        return

    if expired or capped or orphaned:
        logger.info(
            "Notification housekeeping",
            expired=expired,
            over_cap=capped,
            orphaned=orphaned,
            retention_days=RETENTION_DAYS,
        )
