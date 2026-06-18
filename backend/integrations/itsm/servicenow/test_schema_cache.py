from unittest.mock import MagicMock, patch

import pytest

from iam.models import Folder
from integrations.models import (
    IntegrationConfiguration,
    IntegrationProvider,
    IntegrationSchemaCache,
)
from integrations.registry import IntegrationRegistry


@pytest.fixture
def servicenow_config(db):
    Folder.objects.get_or_create(
        content_type=Folder.ContentType.ROOT,
        defaults={"name": "Global"},
    )
    provider, _ = IntegrationProvider.objects.get_or_create(
        name="servicenow", provider_type="itsm"
    )
    return IntegrationConfiguration.objects.create(
        provider=provider,
        credentials={
            "instance_url": "https://example.service-now.com",
            "username": "u",
            "password": "p",
        },
        settings={
            "table_name": "incident",
            "field_map": {"status": "state"},
            "value_map": {"status": {"to_do": "1"}},
        },
        webhook_secret="secret",
    )


def _mock_client():
    client = MagicMock()
    client.get_available_tables.return_value = [
        {"name": "incident", "label": "Incident"}
    ]
    client.get_table_columns.return_value = [{"name": "state", "label": "State"}]
    client.get_field_choices.return_value = [{"value": "1", "label": "New"}]
    return client


def _orchestrator(config, client):
    with patch(
        "integrations.itsm.servicenow.integration.ServiceNowOrchestrator._get_client",
        return_value=client,
    ):
        return IntegrationRegistry.get_orchestrator(config)


def test_get_tables_cache_miss_fetches_and_stores(servicenow_config):
    client = _mock_client()
    orchestrator = _orchestrator(servicenow_config, client)

    result = orchestrator.execute_action("get_tables", {})

    assert result == [{"name": "incident", "label": "Incident"}]
    client.get_available_tables.assert_called_once()
    cache = IntegrationSchemaCache.objects.get(configuration=servicenow_config)
    assert cache.tables == result
    assert cache.fetched_at is not None


def test_get_tables_cache_hit_skips_client(servicenow_config):
    client = _mock_client()
    orchestrator = _orchestrator(servicenow_config, client)

    orchestrator.execute_action("get_tables", {})  # miss -> populate
    client.get_available_tables.reset_mock()

    result = orchestrator.execute_action("get_tables", {})  # hit

    assert result == [{"name": "incident", "label": "Incident"}]
    client.get_available_tables.assert_not_called()


def test_get_columns_and_choices_are_cached(servicenow_config):
    client = _mock_client()
    orchestrator = _orchestrator(servicenow_config, client)

    orchestrator.execute_action("get_columns", {"table_name": "incident"})
    orchestrator.execute_action("get_columns", {"table_name": "incident"})
    orchestrator.execute_action(
        "get_choices", {"table_name": "incident", "field_name": "state"}
    )
    orchestrator.execute_action(
        "get_choices", {"table_name": "incident", "field_name": "state"}
    )

    client.get_table_columns.assert_called_once_with("incident")
    client.get_field_choices.assert_called_once_with("incident", "state")
    cache = IntegrationSchemaCache.objects.get(configuration=servicenow_config)
    assert cache.columns["incident"] == [{"name": "state", "label": "State"}]
    assert cache.choices["incident:state"] == [{"value": "1", "label": "New"}]


def test_refresh_schema_overwrites_stale_cache(servicenow_config):
    IntegrationSchemaCache.objects.create(
        configuration=servicenow_config,
        tables=[{"name": "stale", "label": "Stale"}],
        columns={"incident": [{"name": "old", "label": "Old"}]},
        choices={"incident:state": [{"value": "9", "label": "Old"}]},
    )
    client = _mock_client()
    orchestrator = _orchestrator(servicenow_config, client)

    result = orchestrator.execute_action("refresh_schema", {})

    assert result == [{"name": "incident", "label": "Incident"}]
    # Force re-fetch of the page-load set.
    client.get_available_tables.assert_called_once()
    client.get_table_columns.assert_called_once_with("incident")
    client.get_field_choices.assert_called_once_with("incident", "state")

    cache = IntegrationSchemaCache.objects.get(configuration=servicenow_config)
    assert cache.tables == [{"name": "incident", "label": "Incident"}]
    assert cache.columns["incident"] == [{"name": "state", "label": "State"}]
    assert cache.choices["incident:state"] == [{"value": "1", "label": "New"}]
    assert cache.fetched_at is not None
