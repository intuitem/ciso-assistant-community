import functools
import importlib
import json

from django.conf import settings as django_settings
from django.core.cache import cache

from global_settings.models import GlobalSettings
from global_settings.serializers import FeatureFlagsSerializer
import structlog

logger = structlog.get_logger(__name__)

FEATURE_FLAGS_CACHE_KEY = "global_settings.feature_flags"
# With the default LocMemCache this is per-process: the invalidation at the
# write points is immediate in the worker that handled the write; other
# workers converge within the TTL.
FEATURE_FLAGS_CACHE_TTL = 30  # seconds

_CACHE_MISS = object()

SETTINGS_MASK_PLACEHOLDER = "**********"

# Secret keys, at any depth, across all GlobalSettings categories: the mask
# callable only sees the value JSON, not the row name, so we redact their union.
SENSITIVE_SETTINGS_KEYS = frozenset({"openai_api_key", "secret", "key", "private_key"})


def _redact_keys(obj, keys):
    if isinstance(obj, dict):
        changed = False
        out = {}
        for k, v in obj.items():
            if k in keys and v not in (None, "", {}, []):
                out[k] = SETTINGS_MASK_PLACEHOLDER
                changed = True
            else:
                out[k], sub = _redact_keys(v, keys)
                changed = changed or sub
        return out, changed
    if isinstance(obj, list):
        changed = False
        out = []
        for item in obj:
            new_item, sub = _redact_keys(item, keys)
            out.append(new_item)
            changed = changed or sub
        return out, changed
    return obj, False


def _redact_all_values(obj):
    if isinstance(obj, dict):
        return {k: _redact_all_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_all_values(item) for item in obj]
    return SETTINGS_MASK_PLACEHOLDER


def mask_sensitive_settings(value: str) -> str:
    """Redact secret keys from a GlobalSettings value blob, keeping non-secret
    settings visible so the audit log still shows a readable diff."""
    try:
        data = json.loads(value)
    except ValueError, TypeError:
        return value
    if not isinstance(data, (dict, list)):
        return value
    masked, changed = _redact_keys(data, SENSITIVE_SETTINGS_KEYS)
    if not changed:
        return value
    return json.dumps(masked, sort_keys=True)


def redact_secret_value(value: str) -> str:
    """Fully redact a wholly-secret field (credentials, auth headers, secrets):
    bare strings collapse to the placeholder; JSON objects keep keys but redact
    every leaf value."""
    if not value:
        return value
    try:
        data = json.loads(value)
    except ValueError, TypeError:
        return SETTINGS_MASK_PLACEHOLDER
    if isinstance(data, (dict, list)):
        return json.dumps(_redact_all_values(data), sort_keys=True)
    return SETTINGS_MASK_PLACEHOLDER


def _edition_feature_flags_serializer():
    """The FeatureFlags serializer of this edition — the single source of truth
    for the flag vocabulary, their defaults and which of them a user may hide.
    The enterprise overlay swaps it in via MODULE_PATHS["serializers"], so no
    separate flag list exists anywhere."""
    serializer_class = FeatureFlagsSerializer
    module_path = django_settings.MODULE_PATHS.get("serializers")
    if module_path:
        module = importlib.import_module(module_path)
        serializer_class = getattr(module, "FeatureFlagsSerializer", serializer_class)
    return serializer_class


@functools.cache
def get_supported_feature_flags() -> frozenset:
    """Flags supported by this edition."""
    return frozenset(
        field.source.split(".")[-1]
        for field in _edition_feature_flags_serializer()().fields.values()
        if getattr(field, "source", None) and field.source.startswith("value.")
    )


@functools.cache
def get_user_hideable_feature_flags() -> frozenset:
    """Flags a user may switch off for themselves. Intersected with the
    supported set so an edition can never declare one it doesn't have."""
    declared = getattr(
        _edition_feature_flags_serializer(), "USER_HIDEABLE_FLAGS", frozenset()
    )
    return frozenset(declared) & get_supported_feature_flags()


def get_feature_flag_defaults() -> dict:
    """The value each supported flag takes when nothing was chosen, read off the
    edition's serializer like `get_supported_feature_flags`."""
    from rest_framework.fields import empty

    serializer_class = _edition_feature_flags_serializer()
    defaults = {}
    for field in serializer_class().fields.values():
        source = getattr(field, "source", None)
        if not source or not source.startswith("value."):
            continue
        if field.default is not empty:
            defaults[source.split(".")[-1]] = field.default
    return defaults


def clear_feature_flags_cache():
    cache.delete(FEATURE_FLAGS_CACHE_KEY)


def get_feature_flags() -> dict | None:
    """Return the feature-flags dict, cached for FEATURE_FLAGS_CACHE_TTL
    seconds so per-request RBAC resolution doesn't hit the settings table.
    Returns None when the row is absent or malformed — warned once per TTL,
    not once per flag check."""
    flags = cache.get(FEATURE_FLAGS_CACHE_KEY, _CACHE_MISS)
    if flags is not _CACHE_MISS:
        return flags
    ff_settings = (
        GlobalSettings.objects.filter(name=GlobalSettings.Names.FEATURE_FLAGS)
        .only("value")
        .first()
    )
    if ff_settings is None or not isinstance(ff_settings.value, dict):
        logger.warning("Feature flags settings not found, returning False")
        flags = None
    else:
        flags = ff_settings.value
    cache.set(FEATURE_FLAGS_CACHE_KEY, flags, FEATURE_FLAGS_CACHE_TTL)
    return flags


def ff_is_enabled(feature_flag: str):
    if feature_flag not in get_supported_feature_flags():
        # Not a flag of this edition (e.g. an enterprise-only flag on CE):
        # False by construction, without touching the settings row.
        return False

    flags = get_feature_flags()
    if flags is None:
        return False

    if (flag := flags.get(feature_flag)) is None:
        logger.warning(
            "Feature flag not found, returning False", feature_flag=feature_flag
        )
        return False

    return flag


USER_FEATURE_FLAGS_PREFERENCE_KEY = "feature_flags"


def get_user_hidden_feature_flags(user) -> dict:
    """The user's own hide choices, sanitised: only supported, hideable flags,
    and only the value False. Stored sparse — a flag the user never touched is
    absent, so a flag added by a release is visible without a backfill."""
    preferences = getattr(user, "preferences", None)
    stored = (
        preferences.get(USER_FEATURE_FLAGS_PREFERENCE_KEY)
        if isinstance(preferences, dict)
        else None
    )
    if not isinstance(stored, dict):
        return {}
    hideable = get_user_hideable_feature_flags()
    return {
        name: False
        for name, value in stored.items()
        if value is False and name in hideable
    }


def get_instance_feature_flags() -> dict:
    """Every supported flag with its instance-wide value: the row, backed by the
    declared defaults for the keys a release added and the row has not caught up
    with yet.

    Restricted to the supported set, because an env-gated flag (chat_mode,
    infra_config_management) may linger in the row after being switched off and
    the serializer drops it from the admin view — this must match.
    """
    supported = get_supported_feature_flags()
    stored = {
        name: value
        for name, value in (get_feature_flags() or {}).items()
        if name in supported
    }
    return get_feature_flag_defaults() | stored


def resolve_feature_flags(user) -> dict:
    """The flags as *this user* should see them: the instance flags, narrowed by
    the user's own hide choices.

    Narrowing only, by construction — a user choice can turn a flag off, never
    on. That is what keeps `ff_is_enabled` out of this: enforcement stays
    instance-wide and correct, and this resolution only drives what the UI
    offers. Callers that gate access must keep using `ff_is_enabled`.
    """
    return get_instance_feature_flags() | get_user_hidden_feature_flags(user)


def idp_group_role_inheritance_enabled() -> bool:
    return ff_is_enabled("idp_groups") or ff_is_enabled("jit_provisioning")


def general_setting_is_enabled(key: str) -> bool:
    """Check whether a boolean key in the 'general' GlobalSettings is enabled.
    Returns False when the settings row or the key is missing."""
    gs = GlobalSettings.objects.filter(name="general").only("value").first()
    if gs is None or not isinstance(gs.value, dict):
        return False
    return bool(gs.value.get(key, False))
