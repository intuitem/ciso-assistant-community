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


@functools.cache
def get_supported_feature_flags() -> frozenset:
    """Flags supported by this edition, derived from the edition's
    FeatureFlags serializer — the single source of truth. The enterprise
    overlay swaps that serializer in via MODULE_PATHS["serializers"], so no
    separate flag list exists anywhere."""
    serializer_class = FeatureFlagsSerializer
    module_path = django_settings.MODULE_PATHS.get("serializers")
    if module_path:
        module = importlib.import_module(module_path)
        serializer_class = getattr(module, "FeatureFlagsSerializer", serializer_class)
    return frozenset(
        field.source.split(".")[-1]
        for field in serializer_class().fields.values()
        if getattr(field, "source", None) and field.source.startswith("value.")
    )


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


def general_setting_is_enabled(key: str) -> bool:
    """Check whether a boolean key in the 'general' GlobalSettings is enabled.
    Returns False when the settings row or the key is missing."""
    gs = GlobalSettings.objects.filter(name="general").only("value").first()
    if gs is None or not isinstance(gs.value, dict):
        return False
    return bool(gs.value.get(key, False))
