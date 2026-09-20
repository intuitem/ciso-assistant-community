"""
The admin channel matrix: which channels carry which notification type.

Three layers, each able only to subtract (docs/notification_center_shaping.md §7):
the registry declares what a type supports and defaults them all on; this matrix
narrows that; per-user preferences would narrow it further and do not exist.

The two channels are stored separately, and deliberately so:

  in_app  GlobalSettings(name="general").value["notification_channels"]
  email   GlobalSettings(name="general").value["disabled_email_templates"]

`disabled_email_templates` predates all of this and already governs email everywhere
(`is_email_template_enabled`, the enterprise override page). Migrating it into a new
structure would mean rewriting an admin's existing choices; reading it as the email
column instead means the matrix reports and edits the truth that is already there.
"""

import structlog
from global_settings.models import GlobalSettings

from notifications.registry import NOTIFICATION_REGISTRY

logger = structlog.getLogger(__name__)

IN_APP_KEY = "notification_channels"
EMAIL_KEY = "disabled_email_templates"


def _general() -> GlobalSettings:
    settings, _ = GlobalSettings.objects.get_or_create(
        name="general", defaults={"value": {}}
    )
    if not isinstance(settings.value, dict):
        settings.value = {}
    return settings


def _in_app_overrides() -> dict:
    overrides = _general().value.get(IN_APP_KEY, {})
    return overrides if isinstance(overrides, dict) else {}


def in_app_allowed(notification_type: str) -> bool:
    """Whether the matrix permits an inbox row for this type.

    The registry is the ceiling: an admin may turn a channel off, never on for a type
    that does not support it. An absent entry means "not narrowed", i.e. the registry
    default — so a type added by a release is on without anyone touching settings.
    """
    entry = NOTIFICATION_REGISTRY.get(notification_type)
    if not entry or "in_app" not in entry["channels"]:
        return False
    return bool(_in_app_overrides().get(notification_type, True))


def matrix() -> list[dict]:
    """Every type with its current channel state, for the settings UI."""
    overrides = _in_app_overrides()
    disabled_emails = set(_general().value.get(EMAIL_KEY, []) or [])
    rows = []
    for key, entry in NOTIFICATION_REGISTRY.items():
        supports_in_app = "in_app" in entry["channels"]
        supports_email = "email" in entry["channels"]
        rows.append(
            {
                "type": key,
                "category": entry["category"],
                "mode": entry["mode"],
                "supports_in_app": supports_in_app,
                "supports_email": supports_email,
                "in_app": supports_in_app and bool(overrides.get(key, True)),
                "email": supports_email and key not in disabled_emails,
            }
        )
    return sorted(rows, key=lambda row: (row["category"], row["type"]))


def set_channel(notification_type: str, channel: str, enabled: bool) -> None:
    """Narrow or restore one channel for one type.

    Raises ValueError rather than silently ignoring an unsupported combination: an
    admin toggling something the registry forbids should see it fail, not watch the
    switch spring back with no explanation.
    """
    entry = NOTIFICATION_REGISTRY.get(notification_type)
    if entry is None:
        raise ValueError(f"unknown notification type: {notification_type}")
    if channel not in ("in_app", "email"):
        raise ValueError(f"unknown channel: {channel}")
    if channel not in entry["channels"]:
        raise ValueError(f"{notification_type} does not support {channel}")

    settings = _general()
    if channel == "in_app":
        overrides = dict(_in_app_overrides())
        overrides[notification_type] = enabled
        settings.value[IN_APP_KEY] = overrides
    else:
        disabled = {
            key for key in (settings.value.get(EMAIL_KEY) or []) if isinstance(key, str)
        }
        disabled.discard(notification_type) if enabled else disabled.add(
            notification_type
        )
        settings.value[EMAIL_KEY] = sorted(disabled)

    settings.save(update_fields=["value"])
    logger.info(
        "Notification channel changed",
        type=notification_type,
        channel=channel,
        enabled=enabled,
    )
