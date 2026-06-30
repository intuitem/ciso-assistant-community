"""Model-aware mapper tests for the Asset model (no DB).

These exercise the per-model field_map/value_map plumbing for both providers and
assert that Jira's AppliedControl defaults do NOT leak into other models.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from integrations.itsm.jira.mapper import JiraFieldMapper
from integrations.itsm.servicenow.mapper import ServiceNowFieldMapper


def _config(settings):
    cfg = MagicMock()
    cfg.settings = settings
    return cfg


def _asset(**kwargs):
    base = {
        "name": None,
        "description": None,
        "ref_id": None,
        "type": None,
        "reference_link": None,
        "observation": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


ASSET_SETTINGS = {
    "models": {
        "asset": {
            "table_name": "cmdb_ci",
            "field_map": {"name": "u_name", "type": "u_type"},
            "value_map": {"type": {"PR": "primary", "SP": "support"}},
        }
    }
}


def test_servicenow_asset_to_remote_uses_value_map():
    mapper = ServiceNowFieldMapper(_config(ASSET_SETTINGS), "asset")
    remote = mapper.to_remote(_asset(name="DB-1", type="PR"))
    assert remote == {"u_name": "DB-1", "u_type": "primary"}


def test_servicenow_asset_to_local_reverses_value_map():
    mapper = ServiceNowFieldMapper(_config(ASSET_SETTINGS), "asset")
    local = mapper.to_local({"fields": {"u_name": "DB-1", "u_type": "primary"}})
    assert local["name"] == "DB-1"
    assert local["type"] == "PR"


def test_jira_asset_to_remote_uses_value_map():
    settings = {
        "models": {
            "asset": {
                "table_name": "PROJ:Asset",
                "field_map": {"name": "summary", "type": "customfield_1"},
                "value_map": {"type": {"PR": "Primary", "SP": "Support"}},
            }
        }
    }
    mapper = JiraFieldMapper(_config(settings), "asset")
    remote = mapper.to_remote(_asset(name="DB-1", type="SP"))
    assert remote == {"summary": "DB-1", "customfield_1": "Support"}


def test_jira_applied_control_defaults_do_not_leak_to_asset():
    # Empty asset config: Jira must NOT fall back to the AppliedControl
    # _DEFAULT_FIELD_MAP (name->summary, status->status, ...).
    mapper = JiraFieldMapper(_config({"models": {"asset": {}}}), "asset")
    assert mapper.field_map == {}
    assert mapper.value_map_to_remote == {}


def test_jira_applied_control_defaults_still_apply():
    # Regression: with no config, applied_control keeps its legacy defaults.
    mapper = JiraFieldMapper(_config({}), "applied_control")
    assert mapper.field_map["name"] == "summary"
    assert mapper.value_map_to_remote["status"]["to_do"] == "To Do"
