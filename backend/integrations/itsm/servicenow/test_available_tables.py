from unittest.mock import MagicMock, patch

import pytest

from integrations.models import IntegrationConfiguration

from .client import TABLES_PAGE_SIZE, ServiceNowClient, is_excluded_table


@pytest.fixture
def client():
    mock_config = MagicMock(spec=IntegrationConfiguration)
    mock_config.credentials = {
        "instance_url": "https://example.service-now.com",
        "username": "u",
        "password": "p",
    }
    mock_config.settings = {"table_name": "incident"}
    with patch("integrations.itsm.servicenow.client.check_integration_url"):
        return ServiceNowClient(mock_config)


def _response(records, has_next=False):
    response = MagicMock()
    response.json.return_value = {"result": records}
    response.links = {"first": {}, "last": {}}
    if has_next:
        response.links["next"] = {}
    return response


@pytest.mark.parametrize(
    "name",
    [
        "incident",
        "sn_customerservice_case",
        "sn_si_incident",
        "sn_grc_issue",
        "cmdb_ci_ip_router",
        "cmdb_ci_hyper_v_server",
        "cmn_location",
        "u_dev_request",
    ],
)
def test_user_facing_tables_are_kept(name):
    assert not is_excluded_table(name)


@pytest.mark.parametrize(
    "name",
    [
        "sys_user",
        "syslog_transaction",
        "imp_computer",
        "u_imp_users",
        "x_acme_app_imp_assets",
        "v_plugin",
        "m2m_kb_task",
        "cmdb_ci_m2m_x",
        "sc_cat_item",
    ],
)
def test_noise_tables_are_excluded(name):
    assert is_excluded_table(name)


@patch("integrations.itsm.servicenow.client.requests.get")
def test_get_available_tables_filters_and_sorts(mock_get, client):
    mock_get.return_value = _response(
        [
            {"name": "sys_user", "label": "User"},
            {"name": "u_assets", "label": "assets"},
            {"name": "sn_customerservice_case", "label": "Case"},
            {"name": "incident", "label": "Incident"},
        ]
    )

    tables = client.get_available_tables()

    assert [t["name"] for t in tables] == [
        "u_assets",
        "sn_customerservice_case",
        "incident",
    ]
    query = mock_get.call_args[1]["params"]["sysparm_query"]
    assert [c for c in query.split("^") if "LIKE" in c] == [
        "nameNOT LIKEm2m",
        "nameNOT LIKEimp_",
    ]


@patch("integrations.itsm.servicenow.client.requests.get")
def test_get_available_tables_pages_past_acl_short_page(mock_get, client):
    """A page shortened by ACLs is not the last one while the Link header says next."""
    mock_get.side_effect = [
        _response([{"name": "incident", "label": "Incident"}], has_next=True),
        _response([{"name": "sn_customerservice_case", "label": "Case"}]),
    ]

    tables = client.get_available_tables()

    assert [t["name"] for t in tables] == ["sn_customerservice_case", "incident"]
    offsets = [c[1]["params"]["sysparm_offset"] for c in mock_get.call_args_list]
    assert offsets == [0, TABLES_PAGE_SIZE]


@patch("integrations.itsm.servicenow.client.requests.get")
def test_get_available_tables_without_link_header_uses_page_length(mock_get, client):
    full_page = [{"name": f"u_t{i}", "label": f"T{i}"} for i in range(TABLES_PAGE_SIZE)]
    first, second = _response(full_page), _response([{"name": "u_x", "label": "X"}])
    first.links = second.links = {}
    mock_get.side_effect = [first, second]

    tables = client.get_available_tables()

    assert len(tables) == TABLES_PAGE_SIZE + 1
    assert mock_get.call_count == 2
