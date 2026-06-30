"""Pure unit tests for per-model settings access (no DB)."""

from integrations.settings_access import (
    configured_model_keys,
    get_model_settings,
    is_model_configured,
)


def test_legacy_top_level_resolves_as_applied_control():
    settings = {
        "table_name": "incident",
        "field_map": {"name": "short_description"},
        "value_map": {"status": {"to_do": "1"}},
        "enable_outgoing_sync": True,
    }
    ms = get_model_settings(settings, "applied_control")
    assert ms["table_name"] == "incident"
    assert ms["field_map"] == {"name": "short_description"}
    # Non-mapping keys are not part of the per-model settings.
    assert "enable_outgoing_sync" not in ms


def test_legacy_shim_does_not_apply_to_other_models():
    settings = {"table_name": "incident", "field_map": {"name": "short_description"}}
    assert get_model_settings(settings, "asset") == {}


def test_nested_models_take_precedence():
    settings = {
        "table_name": "incident",
        "models": {
            "applied_control": {"table_name": "sn_compliance"},
            "asset": {"table_name": "cmdb_ci", "field_map": {"name": "name"}},
        },
    }
    assert (
        get_model_settings(settings, "applied_control")["table_name"] == "sn_compliance"
    )
    assert get_model_settings(settings, "asset")["table_name"] == "cmdb_ci"


def test_is_model_configured():
    legacy = {"table_name": "incident"}
    assert is_model_configured(legacy, "applied_control") is True
    assert is_model_configured(legacy, "asset") is False

    asset_only = {"models": {"asset": {"table_name": "cmdb_ci"}}}
    assert is_model_configured(asset_only, "asset") is True
    assert is_model_configured(asset_only, "applied_control") is False

    jira_legacy = {"project_key": "PROJ"}
    assert is_model_configured(jira_legacy, "applied_control") is True

    assert is_model_configured({}, "applied_control") is False


def test_configured_model_keys():
    settings = {
        "table_name": "incident",
        "models": {"asset": {"table_name": "cmdb_ci"}},
    }
    keys = set(configured_model_keys(settings))
    assert keys == {"applied_control", "asset"}
