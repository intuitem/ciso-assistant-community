"""Per-model access to an IntegrationConfiguration's ``settings``.

Mapping config is stored nested per syncable model under
``settings["models"][model_key]``. For backward compatibility, configs created
before this change keep their mapping at the top level of ``settings``; those
legacy keys are read (never rewritten or deleted) as the ``applied_control``
entry via a non-destructive shim.
"""

from __future__ import annotations

# Top-level settings keys that, on legacy configs, constitute the implicit
# "applied_control" mapping.
_LEGACY_MODEL_KEYS = (
    "table_name",
    "field_map",
    "value_map",
    "project_key",
    "issue_type",
    "base_query",
)


def get_model_settings(config_settings: dict | None, model_key: str) -> dict:
    """Return the mapping settings for ``model_key`` (table_name/field_map/...).

    Resolution order: explicit ``settings.models[model_key]``, then the legacy
    top-level shim for ``applied_control``, otherwise an empty dict.
    """
    config_settings = config_settings or {}
    models = config_settings.get("models") or {}
    if model_key in models:
        return models[model_key] or {}
    if model_key == "applied_control":
        return {
            k: config_settings[k] for k in _LEGACY_MODEL_KEYS if k in config_settings
        }
    return {}


def is_model_configured(config_settings: dict | None, model_key: str) -> bool:
    """True if the config has a usable target for ``model_key``.

    A model counts as configured once it has a remote target (a ServiceNow
    table_name, or a Jira project_key) or any field mapping.
    """
    ms = get_model_settings(config_settings, model_key)
    return bool(ms.get("table_name") or ms.get("project_key") or ms.get("field_map"))


def configured_model_keys(config_settings: dict | None) -> list[str]:
    """All model keys this config has a mapping for (nested + legacy implicit)."""
    from integrations.syncable import SYNCABLE_MODELS

    return [key for key in SYNCABLE_MODELS if is_model_configured(config_settings, key)]
