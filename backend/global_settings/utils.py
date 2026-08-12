import json

from global_settings.models import GlobalSettings
from global_settings.serializers import FeatureFlagsSerializer
import structlog

logger = structlog.get_logger(__name__)

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


def ff_is_enabled(feature_flag: str):
    ff_settings = GlobalSettings.objects.filter(
        name=GlobalSettings.Names.FEATURE_FLAGS
    ).first()
    if ff_settings is None:
        logger.warning(
            "Feature flags settings not found, returning False",
            feature_flag=feature_flag,
        )
        return False

    flags: dict[str, bool] = ff_settings.value

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
