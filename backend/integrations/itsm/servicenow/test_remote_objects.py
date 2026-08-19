from unittest.mock import MagicMock, patch

import pytest

from integrations.models import IntegrationConfiguration

from .client import ServiceNowClient


@pytest.fixture
def configuration():
    mock_config = MagicMock(spec=IntegrationConfiguration)
    mock_config.credentials = {
        "instance_url": "https://example.service-now.com",
        "username": "u",
        "password": "p",
    }
    mock_config.settings = {"table_name": "incident", "base_query": "active=true"}
    return mock_config


def _client(configuration):
    with patch("integrations.itsm.servicenow.client.check_integration_url"):
        return ServiceNowClient(configuration)


def _response(records):
    response = MagicMock()
    response.json.return_value = {"result": records}
    return response


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_list_remote_objects_passes_limit(mock_get, mock_sync, configuration):
    mock_get.return_value = _response([])
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = _client(configuration)
    client.list_remote_objects({"limit": 20})

    params = mock_get.call_args[1]["params"]
    assert params["sysparm_limit"] == 20
    assert params["sysparm_query"] == "active=true"


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_list_remote_objects_search_ors_full_subqueries(
    mock_get, mock_sync, configuration
):
    """Each searched field gets its own ^NQ branch carrying the base query."""
    mock_get.return_value = _response([])
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = _client(configuration)
    client.list_remote_objects({"search": "INC001"})

    query = mock_get.call_args[1]["params"]["sysparm_query"]
    assert query == (
        "active=true^numberLIKEINC001"
        "^NQactive=true^short_descriptionLIKEINC001"
        "^NQactive=true^nameLIKEINC001"
    )


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_list_remote_objects_strips_query_metacharacters(
    mock_get, mock_sync, configuration
):
    mock_get.return_value = _response([])
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = _client(configuration)
    client.list_remote_objects({"search": "a^b,c"})

    query = mock_get.call_args[1]["params"]["sysparm_query"]
    assert "^NQ" in query
    assert "LIKEabc" in query


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_list_remote_objects_hydrates_ids_even_when_mapped(
    mock_get, mock_sync, configuration
):
    mock_get.return_value = _response(
        [{"sys_id": "abc123", "number": "INC001", "short_description": "Mapped"}]
    )
    mock_sync.objects.filter.return_value.values_list.return_value = ["abc123"]

    client = _client(configuration)
    results = client.list_remote_objects({"id": "abc123"})

    query = mock_get.call_args[1]["params"]["sysparm_query"]
    assert query == "active=true^sys_idINabc123"
    assert [r["id"] for r in results] == ["abc123"]


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_list_remote_objects_excludes_mapped_records(
    mock_get, mock_sync, configuration
):
    mock_get.return_value = _response(
        [
            {"sys_id": "used1", "number": "INC001", "short_description": "Linked"},
            {"sys_id": "free1", "number": "INC002", "short_description": "Free"},
        ]
    )
    mock_sync.objects.filter.return_value.values_list.return_value = ["used1"]

    client = _client(configuration)
    results = client.list_remote_objects()

    assert [r["id"] for r in results] == ["free1"]
