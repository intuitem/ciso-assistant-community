"""The admin channel matrix: which channels carry which notification type.

Layers can only subtract (docs §7): the registry is the ceiling, this matrix narrows
it, per-user preferences would narrow further and do not exist.

  in_app  GlobalSettings(name="general").value["notification_channels"]
  email   GlobalSettings(name="general").value["disabled_email_templates"]

`disabled_email_templates` predates this and already governs email everywhere, so it
is read as the email column rather than migrated -- an admin's existing choices stay
where they are.

Account types (password_reset, welcome, welcome_sso) are switchable like any other:
the confirm-before-disabling guard the enterprise template page used to show was
retired with that page's toggle, deliberately. Muting them blocks the flow they
carry -- User.mailing() skips a disabled template -- which the settings tab says.
"""

import structlog
from global_settings.models import GlobalSettings

from notifications.registry import NOTIFICATION_REGISTRY

logger = structlog.getLogger(__name__)

IN_APP_KEY = "notification_channels"
EMAIL_KEY = "disabled_email_templates"


def _general() -> GlobalSettings:
    """The writable row. Readers use `_general_value`, which does not create a settings
    row as a side effect of being asked a question."""
    settings, _ = GlobalSettings.objects.get_or_create(
        name="general", defaults={"value": {}}
    )
    if not isinstance(settings.value, dict):
        settings.value = {}
    return settings


def _general_value() -> dict:
    settings = GlobalSettings.objects.filter(name="general").only("value").first()
    value = settings.value if settings is not None else None
    return value if isinstance(value, dict) else {}


def _in_app_overrides() -> dict:
    overrides = _general_value().get(IN_APP_KEY, {})
    return overrides if isinstance(overrides, dict) else {}


def in_app_allowed(notification_type: str) -> bool:
    """Whether the matrix permits an inbox row for this type. An absent entry means
    "not narrowed", so a type added by a release is on with no settings change."""
    entry = NOTIFICATION_REGISTRY.get(notification_type)
    if not entry or "in_app" not in entry["channels"]:
        return False
    return bool(_in_app_overrides().get(notification_type, True))


def matrix() -> list[dict]:
    """Every type with its current channel state, for the settings UI."""
    general = _general_value()
    overrides = general.get(IN_APP_KEY, {})
    overrides = overrides if isinstance(overrides, dict) else {}
    disabled_emails = set(general.get(EMAIL_KEY, []) or [])
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
    """Narrow or restore one channel for one type. Raises rather than ignoring an
    unsupported combination, so the switch does not silently spring back."""
    entry = NOTIFICATION_REGISTRY.get(notification_type)
    if entry is None:
        raise ValueError(f"unknown notification type: {notification_type}")
    if channel not in ("in_app", "email"):
        raise ValueError(f"unknown channel: {channel}")
    if channel not in entry["channels"]:
        raise ValueError(f"{notification_type} does not support {channel}")

    settings = _general()
    if channel == "in_app":
        overrides = settings.value.get(IN_APP_KEY, {})
        overrides = dict(overrides) if isinstance(overrides, dict) else {}
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
