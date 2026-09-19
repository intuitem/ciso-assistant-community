import re
from functools import lru_cache
from pathlib import Path
from string import Template

import structlog
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils.translation import get_language

import yaml

from iam.models import Folder, User
from notifications.models import Notification
from notifications.registry import NOTIFICATION_REGISTRY

logger = structlog.getLogger(__name__)

TITLES_PATH = Path(__file__).parent / "titles"
DEFAULT_LOCALE = "en"
UNRESOLVED = re.compile(r"\$\{[a-z_]+\}")

# Rows are pruned by the condition going false (below), not by age. 90 days mirrors
# AUDITLOG_RETENTION_DAYS and is the backstop for the event types.
RETENTION_DAYS = 90


@lru_cache(maxsize=None)
def _titles(locale: str) -> dict:
    path = TITLES_PATH / f"{locale}.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def resolve_title(notification_type: str, locale: str | None = None) -> str | None:
    """
    The inbox row title for a notification type, unrendered.

    Read from the notification layer, never from the email templates, so an
    enterprise `CustomEmailTemplate` override cannot reach it: those store subject
    and body only, and replace the built-in file rather than merging over it.

    Returns None for a type with no in-app channel, which has no title by design.
    """
    if notification_type not in NOTIFICATION_REGISTRY:
        logger.warning("Unknown notification type", type=notification_type)
        return None

    locale = (locale or get_language() or DEFAULT_LOCALE).split("-")[0].lower()
    return _titles(locale).get(notification_type) or _titles(DEFAULT_LOCALE).get(
        notification_type
    )


def in_app_enabled(notification_type: str) -> bool:
    """Whether this type writes inbox rows.

    The registry declares the supported channels and they are all on; an admin may
    narrow them, never widen them. The narrowing layer is enterprise-only and not
    built yet, so today this is the registry alone.
    """
    entry = NOTIFICATION_REGISTRY.get(notification_type)
    return bool(entry) and "in_app" in entry["channels"]


def _render_title(
    notification_type: str, context: dict, locale: str | None
) -> str | None:
    template = resolve_title(notification_type, locale)
    if not template:
        return None
    title = Template(template).safe_substitute(context)
    if leftover := UNRESOLVED.findall(title):
        # safe_substitute leaves the placeholder in place, so this would reach the
        # inbox as literal "${control_name}". The registry's `context` lists what a
        # producer owes; a miss is a producer bug, not a reason to drop the row.
        logger.warning(
            "Notification title has unresolved placeholders",
            type=notification_type,
            missing=leftover,
        )
    return title[: Notification._meta.get_field("title").max_length]


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
    locale: str | None = None,
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

    for user in _as_users(recipients):
        title = _render_title(
            notification_type, context or {}, locale or _locale_for(user)
        )
        if not title:
            continue
        # Only the variables the registry declares for this type: the producers' context
        # dicts also carry email-only material (descriptions, URLs, formatted lists)
        # that the title never uses and the inbox should not store.
        declared = {
            key: str(value)
            for key, value in (context or {}).items()
            if key in entry["context"]
        }
        defaults = {"title": title, "context": declared, "folder": folder}
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


def _locale_for(user: User) -> str:
    try:
        return user.get_preferences().get("lang") or DEFAULT_LOCALE
    except Exception as e:
        logger.warning("Could not resolve user locale", user=user.id, error=e)
        return DEFAULT_LOCALE


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
