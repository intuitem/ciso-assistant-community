from unittest.mock import MagicMock, patch

import pytest

from integrations.models import IntegrationConfiguration

from .client import LIST_ORDERING, ServiceNowClient


@pytest.fixture
def configuration():
    mock_config = MagicMock(spec=IntegrationConfiguration)
    mock_config.credentials = {
        "instance_url": "https://example.service-now.com",
        "username": "u",
        "password": "p",
    }
    mock_config.settings = {"table_name": "incident", "base_query": "active=true"}
    # Empty schema cache: searchable-field resolution falls back to all
    # candidates, like a real config whose columns aren't cached yet.
    mock_config.schema_cache.columns = {}
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
    mock_get.return_value = _response(
        [{"sys_id": f"rec{i}", "number": f"INC{i:03d}"} for i in range(30)]
    )
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = _client(configuration)
    results = client.list_remote_objects({"limit": 20})

    assert len(results) == 20
    assert (
        mock_get.call_args[1]["params"]["sysparm_query"]
        == f"active=true^{LIST_ORDERING}"
    )


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
        f"^NQactive=true^nameLIKEINC001^{LIST_ORDERING}"
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
def test_metacharacter_only_search_returns_nothing(mock_get, mock_sync, configuration):
    """A term that sanitizes to nothing matches nothing, not everything."""
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = _client(configuration)
    results = client.list_remote_objects({"search": "^^, "})

    assert results == []
    mock_get.assert_not_called()


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
    assert query == f"active=true^sys_idINabc123^{LIST_ORDERING}"
    assert [r["id"] for r in results] == ["abc123"]


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_search_scopes_every_base_query_branch(mock_get, mock_sync, configuration):
    """A base_query that itself ORs subqueries with ^NQ gets the search
    condition on every branch; otherwise a branch matches its whole scope."""
    configuration.settings = {
        "table_name": "incident",
        "base_query": "active=true^NQstate=2",
    }
    configuration.schema_cache.columns = {"incident": [{"name": "number"}]}
    mock_get.return_value = _response([])
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = _client(configuration)
    client.list_remote_objects({"search": "INC"})

    query = mock_get.call_args[1]["params"]["sysparm_query"]
    assert query == f"active=true^numberLIKEINC^NQstate=2^numberLIKEINC^{LIST_ORDERING}"


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_hydration_scopes_every_base_query_branch(mock_get, mock_sync, configuration):
    configuration.settings = {
        "table_name": "incident",
        "base_query": "active=true^NQstate=2",
    }
    mock_get.return_value = _response([])
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = _client(configuration)
    client.list_remote_objects({"id": "abc123"})

    query = mock_get.call_args[1]["params"]["sysparm_query"]
    assert query == (
        f"active=true^sys_idINabc123^NQstate=2^sys_idINabc123^{LIST_ORDERING}"
    )


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_empty_base_query_appends_bare_condition(mock_get, mock_sync, configuration):
    """An empty base_query must not produce a leading ^ in the encoded query."""
    configuration.settings = {"table_name": "incident", "base_query": ""}
    mock_get.return_value = _response([])
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = _client(configuration)
    client.list_remote_objects({"id": "abc123"})

    query = mock_get.call_args[1]["params"]["sysparm_query"]
    assert query == f"sys_idINabc123^{LIST_ORDERING}"


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


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_hydration_rejects_metacharacter_ids(mock_get, mock_sync, configuration):
    """A crafted id cannot inject an extra encoded-query branch."""
    mock_get.return_value = _response([])
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = _client(configuration)
    client.list_remote_objects({"id": "abc123,x^NQactive=false,y^ORactive=false"})

    query = mock_get.call_args[1]["params"]["sysparm_query"]
    assert query == f"active=true^sys_idINabc123^{LIST_ORDERING}"


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_hydration_with_no_valid_ids_skips_remote_call(
    mock_get, mock_sync, configuration
):
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = _client(configuration)
    results = client.list_remote_objects({"id": "x^NQactive=false"})

    assert results == []
    mock_get.assert_not_called()


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_hydration_caps_id_list(mock_get, mock_sync, configuration):
    mock_get.return_value = _response([])
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = _client(configuration)
    client.list_remote_objects({"id": ",".join(f"id{i}" for i in range(500))})

    query = mock_get.call_args[1]["params"]["sysparm_query"]
    assert query.count(",") == 19


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_search_branches_only_cover_existing_columns(
    mock_get, mock_sync, configuration
):
    """A table lacking a candidate field (incident has no ``name``) gets no
    branch for it, since ServiceNow turns the invalid condition into a
    match-everything branch (default) or an empty result (strict mode)."""
    configuration.schema_cache.columns = {
        "incident": [{"name": "number"}, {"name": "short_description"}]
    }
    mock_get.return_value = _response([])
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = _client(configuration)
    client.list_remote_objects({"search": "INC001"})

    query = mock_get.call_args[1]["params"]["sysparm_query"]
    assert query == (
        f"active=true^numberLIKEINC001^NQactive=true^short_descriptionLIKEINC001^{LIST_ORDERING}"
    )


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_search_with_no_valid_columns_returns_nothing(
    mock_get, mock_sync, configuration
):
    """No searchable column means no matches, not the unfiltered base query."""
    configuration.schema_cache.columns = {"incident": [{"name": "state"}]}
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = _client(configuration)
    results = client.list_remote_objects({"search": "INC001"})

    assert results == []
    mock_get.assert_not_called()


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_list_paginates_past_mapped_records(mock_get, mock_sync, configuration):
    """A first page full of mapped records must not shrink the result below
    the limit while more selectable records exist: that would flip the
    picker's lazy/eager probe to eager on a truncated list."""
    mapped = [f"rec{i}" for i in range(100)]
    mock_get.side_effect = [
        _response([{"sys_id": sys_id, "number": "INC"} for sys_id in mapped]),
        _response(
            [{"sys_id": f"rec{i}", "number": f"INC{i:03d}"} for i in range(100, 160)]
        ),
    ]
    mock_sync.objects.filter.return_value.values_list.return_value = mapped

    client = _client(configuration)
    results = client.list_remote_objects({"limit": 51})

    assert len(results) == 51
    assert not set(mapped) & {r["id"] for r in results}
    second_params = mock_get.call_args_list[1][1]["params"]
    assert second_params["sysparm_offset"] == 100


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_list_scan_budget_bounds_pagination(mock_get, mock_sync, configuration):
    """Paging past mapped records stops at MAX_LIST_FETCH scanned rows."""
    mapped = [f"rec{i}" for i in range(1000)]
    mock_get.side_effect = [
        _response(
            [
                {"sys_id": sys_id, "number": "INC"}
                for sys_id in mapped[i * 100 : (i + 1) * 100]
            ]
        )
        for i in range(10)
    ]
    mock_sync.objects.filter.return_value.values_list.return_value = mapped

    client = _client(configuration)
    results = client.list_remote_objects({"limit": 51})

    assert results == []
    assert mock_get.call_count == 5


@patch("integrations.itsm.servicenow.client.SyncMapping")
@patch("integrations.itsm.servicenow.client.requests.get")
def test_search_without_schema_cache_row_keeps_all_branches(
    mock_get, mock_sync, configuration
):
    """A config with no schema cache row falls back to all candidates.

    Accessing the reverse one-to-one raises ObjectDoesNotExist on a real
    config without a cache row; simulate it from inside the guarded lookup.
    """
    from django.core.exceptions import ObjectDoesNotExist

    configuration.schema_cache.columns = MagicMock()
    configuration.schema_cache.columns.get.side_effect = ObjectDoesNotExist()
    mock_get.return_value = _response([])
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = _client(configuration)
    client.list_remote_objects({"search": "INC001"})

    query = mock_get.call_args[1]["params"]["sysparm_query"]
    assert query.count("^NQ") == 2
