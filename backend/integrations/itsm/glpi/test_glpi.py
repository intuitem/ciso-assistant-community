import hashlib
import hmac
import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests

from integrations.models import IntegrationConfiguration

from . import client as client_module
from .client import LIST_PAGE_SIZE, GLPIClient, parse_schema
from .integration import GLPIOrchestrator
from .mapper import GLPIFieldMapper, html_to_text, text_to_html

CREDENTIALS = {
    "instance_url": "https://glpi.example.com",
    "client_id": "cid",
    "client_secret": "csecret",
    "username": "sync",
    "password": "pw",
}

# Trimmed copy of what GLPI 11 and 12 serve at /api.php/v2/doc.json.
OPENAPI = {
    "components": {
        "schemas": {
            "Ticket": {
                "properties": {
                    "id": {"type": "integer", "readOnly": True},
                    "name": {"type": "string"},
                    "is_deleted": {"type": "boolean"},
                    "content": {"type": "string", "format": "html"},
                    "priority": {
                        "type": "integer",
                        "enum": [1, 2, 3, 4, 5],
                        "description": "- 1: Very Low\n- 2: Low\n- 3: Medium\n- 4: High\n- 5: Very High",
                    },
                    "resolution_date": {"type": "string", "format": "date-time"},
                    "status": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "integer",
                                "enum": [1, 2, 4, 5, 6],
                                "description": "- 1: New\n- 2: Processing (assigned)\n- 4: Pending\n- 5: Solved\n- 6: Closed\n",
                            },
                            "name": {"type": "string"},
                        },
                    },
                    "category": {
                        "type": "object",
                        "properties": {"id": {"type": "integer"}},
                    },
                    "team": {"type": "array"},
                }
            },
            "Computer": {
                "properties": {
                    "id": {"type": "integer", "readOnly": True},
                    "name": {"type": "string"},
                    "comment": {"type": "string"},
                    "otherserial": {"type": "string"},
                    "is_deleted": {"type": "boolean"},
                    # A dropdown fed by the instance, not a fixed list.
                    "status": {
                        "type": "object",
                        "properties": {"id": {"type": "integer"}},
                    },
                }
            },
            # Not searchable by name: cannot be offered.
            "Monitor": {"properties": {"id": {"type": "integer"}}},
            # Not an item type this provider syncs.
            "Document": {"properties": {"name": {"type": "string"}}},
        }
    }
}


@pytest.fixture(autouse=True)
def clear_token_cache():
    client_module._TOKEN_CACHE.clear()
    yield
    client_module._TOKEN_CACHE.clear()


def _configuration(settings=None, webhook_secret="whsec"):
    config = MagicMock(spec=IntegrationConfiguration)
    config.credentials = dict(CREDENTIALS)
    config.settings = settings or {}
    config.webhook_secret = webhook_secret
    return config


def _client(settings=None, model_key="applied_control"):
    with patch("integrations.itsm.glpi.client.check_integration_url"):
        return GLPIClient(_configuration(settings), model_key)


ASSET_SETTINGS = {
    "models": {
        "asset": {
            "table_name": "Computer",
            "field_map": {"name": "name", "description": "comment", "type": "contact"},
            "value_map": {"type": {"PR": "primary", "SP": "support"}},
        }
    }
}


def _response(payload=None, status=200):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload
    return response


def _token_response(token="tok", expires_in=3600):
    return _response({"access_token": token, "expires_in": expires_in})


# --- Schema ------------------------------------------------------------------


def test_parse_schema_keeps_synced_types_and_mappable_properties():
    tables, columns, choices = parse_schema(OPENAPI)

    assert tables == [
        {"name": "Ticket", "label": "Tickets"},
        {"name": "Computer", "label": "Computers"},
    ]
    # An asset's status is a free dropdown: not mappable.
    assert {c["name"] for c in columns["Computer"]} == {
        "id",
        "name",
        "comment",
        "otherserial",
        "is_deleted",
    }
    by_name = {c["name"]: c for c in columns["Ticket"]}
    # Scalars and the enum-backed status dropdown; no free dropdowns or arrays.
    assert set(by_name) == {
        "id",
        "name",
        "is_deleted",
        "content",
        "priority",
        "resolution_date",
        "status",
    }
    assert by_name["id"]["readonly"] is True
    assert by_name["content"]["type"] == "html"
    assert choices["Ticket:status"][1] == {
        "value": "2",
        "label": "Processing (assigned)",
    }
    assert choices["Ticket:priority"][-1] == {"value": "5", "label": "Very High"}


# --- Mapper ------------------------------------------------------------------


def test_default_mapping_pushes_a_ticket_payload():
    mapper = GLPIFieldMapper(_configuration())
    control = SimpleNamespace(
        name="Patch servers",
        description="Line one\nA & B",
        status="in_progress",
        priority=1,
        eta=date(2026, 12, 24),
    )

    assert mapper.to_remote(control) == {
        "name": "Patch servers",
        "content": "<p>Line one</p><p>A &amp; B</p>",
        "status": {"id": 2},
        "priority": 5,
        "resolution_date": "2026-12-24",
    }


@pytest.mark.parametrize(
    "item_type, payload",
    [
        ("Ticket", {"status": {"id": 2}}),
        ("Problem", {"status": {"id": 2}}),
        ("Change", {}),
    ],
)
def test_default_status_only_uses_values_the_item_type_has(item_type, payload):
    mapper = GLPIFieldMapper(_configuration({"table_name": item_type}))
    control = SimpleNamespace(status="in_progress")

    assert mapper.to_remote_partial(control, ["status"]) == payload
    # The statuses every type shares are still sent.
    assert mapper.to_remote_partial(SimpleNamespace(status="on_hold"), ["status"]) == {
        "status": {"id": 4}
    }


def test_push_drops_choices_without_a_remote_value():
    mapper = GLPIFieldMapper(_configuration())
    control = SimpleNamespace(status="--", priority=None)

    assert mapper.to_remote_partial(control, ["status", "priority"]) == {}


def test_default_mapping_pulls_an_api_item():
    mapper = GLPIFieldMapper(_configuration())
    item = {
        "id": 7,
        "name": "Renamed in GLPI",
        "content": "<p>Line one</p><p>A &amp; B<br>C</p>",
        "status": {"id": 6, "name": "Closed"},
        "priority": 6,
        # Offset is the instance timezone: the local calendar day is kept.
        "resolution_date": "2026-12-24T00:30:00+02:00",
    }

    assert mapper.to_local({"key": "7", "fields": item}) == {
        "name": "Renamed in GLPI",
        "description": "Line one\nA & B\nC",
        "status": "active",
        "priority": 1,
        "eta": date(2026, 12, 24),
    }


def test_configured_value_map_wins_over_defaults():
    mapper = GLPIFieldMapper(
        _configuration(
            {
                "field_map": {"status": "status"},
                "value_map": {"status": {"deprecated": "6"}},
            }
        )
    )

    assert mapper.to_remote(SimpleNamespace(status="deprecated")) == {
        "status": {"id": 6}
    }
    assert mapper.to_local({"fields": {"status": {"id": 6}}}) == {
        "status": "deprecated"
    }
    # Unmapped by the user, and no default sneaks back in on push.
    assert mapper.to_remote(SimpleNamespace(status="to_do")) == {}


def test_suggest_mapping_only_offers_what_the_item_type_exposes():
    mapper = GLPIFieldMapper(_configuration())
    _, columns, choices = parse_schema(OPENAPI)
    source = MagicMock()
    source.get_table_columns.return_value = [
        c for c in columns["Ticket"] if c["name"] != "resolution_date"
    ]
    source.get_field_choices.side_effect = lambda table, field: [
        c for c in choices[f"{table}:{field}"] if c["value"] != "4"
    ]

    suggestion = mapper.suggest_mapping_for_table("Ticket", source)

    assert "eta" not in suggestion["field_map"]
    assert suggestion["field_map"]["description"] == "content"
    assert "on_hold" not in suggestion["value_map"]["status"]
    assert suggestion["value_map"]["status"]["to_do"] == "1"


def test_asset_mapping_is_only_what_the_settings_name():
    mapper = GLPIFieldMapper(_configuration(ASSET_SETTINGS), "asset")
    asset = SimpleNamespace(
        name="DB server",
        description="Line one\nLine two",
        type="PR",
        ref_id="A-1",
        reference_link=None,
        observation=None,
    )

    # Plain text, not the rich text of a ticket description.
    assert mapper.to_remote(asset) == {
        "name": "DB server",
        "comment": "Line one\nLine two",
        "contact": "primary",
    }
    assert mapper.to_remote_partial(asset, ["type", "ref_id"]) == {"contact": "primary"}
    item = {"id": 2, "name": "Renamed", "comment": "", "contact": "support"}
    assert mapper.to_local({"key": "2", "fields": item}) == {
        "name": "Renamed",
        "type": "SP",
    }

    # No mapping, no sync: the control defaults do not apply to assets.
    unmapped = GLPIFieldMapper(
        _configuration({"models": {"asset": {"table_name": "Computer"}}}), "asset"
    )
    assert unmapped.to_remote(asset) == {}
    assert unmapped.to_local({"fields": item}) == {}


def test_a_number_mapped_to_a_text_field_is_pulled_as_text():
    settings = {"models": {"asset": {"field_map": {"ref_id": "id"}}}}
    mapper = GLPIFieldMapper(_configuration(settings), "asset")

    assert mapper.to_local({"fields": {"id": 12}}) == {"ref_id": "12"}


def test_asset_mapping_suggestion_follows_the_item_type():
    mapper = GLPIFieldMapper(_configuration(), "asset")
    _, columns, _ = parse_schema(OPENAPI)
    source = MagicMock()
    source.get_table_columns.return_value = columns["Computer"]

    assert mapper.suggest_mapping_for_table("Computer", source) == {
        "field_map": {
            "name": "name",
            "description": "comment",
            "ref_id": "otherserial",
        },
        "value_map": {},
    }

    # Software has no inventory number.
    source.get_table_columns.return_value = [
        c for c in columns["Computer"] if c["name"] != "otherserial"
    ]
    suggestion = mapper.suggest_mapping_for_table("Software", source)
    assert "ref_id" not in suggestion["field_map"]


def test_text_that_looks_like_a_number_is_sent_as_text():
    settings = {
        "models": {
            "asset": {
                "field_map": {"type": "contact"},
                "value_map": {"type": {"PR": "007", "SP": "8"}},
            }
        }
    }
    mapper = GLPIFieldMapper(_configuration(settings), "asset")

    assert mapper.to_remote(SimpleNamespace(type="PR")) == {"contact": "007"}
    assert mapper.to_local({"fields": {"contact": "007"}}) == {"type": "PR"}
    # A plain number is an id, as for ticket statuses and priorities.
    assert mapper.to_remote(SimpleNamespace(type="SP")) == {"contact": 8}


def test_rich_text_round_trip():
    text = "First line\nSecond <b> & line"
    assert html_to_text(text_to_html(text)) == text


# --- Client ------------------------------------------------------------------


@patch("integrations.itsm.glpi.client.requests.request")
@patch("integrations.itsm.glpi.client.requests.post")
def test_token_is_requested_once_and_shared_between_clients(mock_post, mock_request):
    mock_post.return_value = _token_response()
    mock_request.return_value = _response({})

    _client().test_connection()
    _client().test_connection()

    assert mock_post.call_count == 1
    grant = mock_post.call_args[1]["data"]
    assert grant["grant_type"] == "password"
    assert grant["scope"] == "api"
    assert mock_post.call_args[0][0] == "https://glpi.example.com/api.php/token"
    assert mock_request.call_args[0][1] == "https://glpi.example.com/api.php/v2/Session"
    assert mock_request.call_args[1]["headers"]["Authorization"] == "Bearer tok"
    assert mock_request.call_args[1]["allow_redirects"] is False


@patch("integrations.itsm.glpi.client.requests.request")
@patch("integrations.itsm.glpi.client.requests.post")
def test_rejected_token_is_renewed_once(mock_post, mock_request):
    mock_post.side_effect = [_token_response("old"), _token_response("new")]
    mock_request.side_effect = [_response(status=401), _response({"id": 3})]

    client = _client()
    client.update_remote_object("3", {"name": "x"})

    assert mock_post.call_count == 2
    assert mock_request.call_args[1]["headers"]["Authorization"] == "Bearer new"
    assert mock_request.call_args[0] == (
        "PATCH",
        "https://glpi.example.com/api.php/v2/Assistance/Ticket/3",
    )


@pytest.mark.parametrize("status", [301, 307])
@patch("integrations.itsm.glpi.client.requests.request")
def test_a_redirected_write_is_a_failure(mock_request, status):
    redirect = requests.Response()
    redirect.status_code = status
    redirect.headers["Location"] = "https://glpi.example.com/elsewhere"
    mock_request.return_value = redirect
    client = _client()
    client._get_token = MagicMock(return_value="tok")

    with pytest.raises(requests.exceptions.HTTPError):
        client.update_remote_object("3", {"name": "x"})
    assert client.test_connection() is False


@pytest.mark.parametrize(
    "settings, refused",
    [
        ({}, False),
        ({"table_name": "Change"}, False),
        ({"models": {"applied_control": {"table_name": "Problem"}}}, False),
        ({"table_name": "Tickets"}, True),
        ({"table_name": ["Ticket"]}, True),
        ({"models": {"applied_control": {"table_name": "../Session"}}}, True),
        ({"models": {"asset": {}}}, False),
        ({"models": {"asset": {"table_name": "Computer"}}}, False),
        (ASSET_SETTINGS, False),
        # Each model has its own item types.
        ({"models": {"asset": {"table_name": "Ticket"}}}, True),
        ({"models": {"applied_control": {"table_name": "Computer"}}}, True),
        ({"models": {"asset": {"table_name": "Custom/Server"}}}, True),
        ({"models": {"asset": {"field_map": []}}}, True),
        ({"models": {"asset": {"value_map": {"type": "PR"}}}}, True),
        ({"models": {"finding": {"table_name": "Ticket"}}}, True),
        ({"models": [{}]}, True),
        ({"models": {"applied_control": True}}, True),
        # Wrong types that are falsy must not pass as "not set".
        ({"models": []}, True),
        ({"models": {"applied_control": False}}, True),
        ({"table_name": []}, True),
        ({"table_name": 0}, True),
        ({"value_map": {"status": ["2"]}}, True),
        ({"value_map": []}, True),
        ({"field_map": {"name": ["name"]}}, True),
        # Null and empty mean "not set".
        ({"models": None, "table_name": None, "field_map": None}, False),
        ({"table_name": "", "field_map": {}, "value_map": {}}, False),
        ({"value_map": {"status": {"to_do": "1"}}}, False),
    ],
)
def test_settings_are_checked_before_a_configuration_is_created(settings, refused):
    assert bool(GLPIOrchestrator.settings_errors(None, settings)) is refused


@pytest.mark.parametrize("table_name", [["Ticket"], {"a": 1}, 3, ""])
def test_rpc_refuses_a_table_name_that_is_not_text(table_name):
    orchestrator = GLPIOrchestrator(_configuration())
    with pytest.raises(ValueError):
        orchestrator.execute_action("get_columns", {"table_name": table_name})


@pytest.mark.parametrize("model_key", ["finding", ["asset"], None])
def test_rpc_refuses_a_model_that_is_not_synced(model_key):
    orchestrator = GLPIOrchestrator(_configuration())
    with pytest.raises(ValueError):
        orchestrator.execute_action("get_tables", {"model_key": model_key})


def test_each_model_is_offered_its_own_item_types():
    orchestrator = GLPIOrchestrator(_configuration())
    tables, columns, choices = parse_schema(OPENAPI)
    cache = MagicMock(tables=tables, columns=columns, choices=choices)
    orchestrator._load_schema = MagicMock(return_value=cache)

    def offered(params):
        return [t["name"] for t in orchestrator.execute_action("get_tables", params)]

    assert offered({}) == ["Ticket"]
    assert offered({"model_key": "applied_control"}) == ["Ticket"]
    assert offered({"model_key": "asset"}) == ["Computer"]

    # A cache filled before assets were synced is reloaded once.
    stale = MagicMock(tables=[{"name": "Ticket", "label": "Tickets"}])
    orchestrator._load_schema = MagicMock(
        side_effect=lambda force=False: cache if force else stale
    )
    assert offered({"model_key": "asset"}) == ["Computer"]


@patch("integrations.itsm.glpi.client.requests.get")
def test_schema_is_fetched_without_the_token(mock_get):
    """GLPI 11.0.0 and 11.0.1 answer 500 when the public document is asked
    for with a token."""
    answer = requests.Response()
    answer.status_code = 200
    answer._content = json.dumps(OPENAPI).encode()
    mock_get.return_value = answer
    client = _client()
    client._get_token = MagicMock(side_effect=AssertionError("no token needed"))

    tables, _, _ = client.fetch_schema()

    assert [t["name"] for t in tables] == ["Ticket", "Computer"]
    assert mock_get.call_args[0][0] == "https://glpi.example.com/api.php/v2/doc.json"
    assert "Authorization" not in mock_get.call_args[1]["headers"]
    assert mock_get.call_args[1]["allow_redirects"] is False


def test_only_synced_models_get_a_client_or_a_mapper():
    orchestrator = GLPIOrchestrator(_configuration(ASSET_SETTINGS))
    with pytest.raises(ValueError):
        orchestrator.mapper_for("finding")
    with pytest.raises(ValueError):
        orchestrator.client_for("finding")
    assert isinstance(orchestrator.mapper_for("applied_control"), GLPIFieldMapper)
    with patch("integrations.itsm.glpi.client.check_integration_url"):
        assert orchestrator.client_for("asset").table == "Computer"
        assert orchestrator.client_for("applied_control").table == "Ticket"


def test_item_type_and_ids_cannot_alter_the_request_path():
    with pytest.raises(ValueError):
        _client({"table_name": "../Setup/Webhook"})._collection_path()
    with pytest.raises(ValueError):
        _client()._item_path("3/../../Session")
    with pytest.raises(ValueError):
        _client()._item_path("../Session:3")


def test_an_id_addresses_an_item_of_the_model_s_own_type():
    tickets = _client()
    assert tickets._item_path("Ticket:3") == "/Assistance/Ticket/3"
    # As given when linking through the API.
    assert tickets._item_path("3") == "/Assistance/Ticket/3"
    # Linked under another type, or an asset id: never read as a ticket.
    for other in ("Change:3", "Computer:3"):
        with pytest.raises(ValueError):
            tickets._item_path(other)

    assets = _client(ASSET_SETTINGS, "asset")
    assert assets._item_path("Computer:7") == "/Assets/Computer/7"
    with pytest.raises(ValueError):
        assets._item_path("Ticket:7")

    # A model only reaches its own item types, and assets have no default.
    for settings in ({}, {"models": {"asset": {"table_name": "Ticket"}}}):
        with pytest.raises(ValueError):
            _client(settings, "asset")._collection_path()
    with pytest.raises(ValueError):
        _client({"table_name": "Computer"})._collection_path()


@patch("integrations.itsm.glpi.client.requests.request")
def test_a_created_item_is_linked_under_its_type(mock_request):
    mock_request.return_value = _response({"id": 12, "href": "/Assets/Computer/12"})
    client = _client(ASSET_SETTINGS, "asset")
    client._get_token = MagicMock(return_value="tok")
    asset = SimpleNamespace(name="DB server", description=None, type=None)

    assert client.create_remote_object(asset) == "Computer:12"
    assert mock_request.call_args[0] == (
        "POST",
        "https://glpi.example.com/api.php/v2/Assets/Computer",
    )
    assert mock_request.call_args[1]["json"] == {"name": "DB server"}

    # Nothing to put in the item: GLPI is not asked to create an empty one.
    mock_request.reset_mock()
    with pytest.raises(ValueError):
        client.create_remote_object(SimpleNamespace(name=None, description=None))
    mock_request.assert_not_called()


@patch("integrations.itsm.glpi.client.SyncMapping")
@patch("integrations.itsm.glpi.client.requests.request")
def test_nothing_is_listed_for_a_model_without_an_item_type(mock_request, mock_sync):
    assert _client({}, "asset").list_remote_objects({"search": "db"}) == []
    mock_request.assert_not_called()


def _list(mock_request, mock_sync, query, pages, mapped=()):
    mock_request.side_effect = [_response(page) for page in pages]
    mock_sync.objects.filter.return_value.values_list.return_value = list(mapped)
    client = _client()
    client._get_token = MagicMock(return_value="tok")
    return client.list_remote_objects(query)


@patch("integrations.itsm.glpi.client.SyncMapping")
@patch("integrations.itsm.glpi.client.requests.request")
def test_list_hides_trashed_and_mapped_items(mock_request, mock_sync):
    results = _list(
        mock_request,
        mock_sync,
        {"limit": 10},
        [[{"id": 2, "name": "Mapped"}, {"id": 1, "name": "Free"}]],
        mapped=["Ticket:2", "Computer:1"],
    )

    # Computer 1 is linked, ticket 1 is not.
    assert results == [{"key": "Ticket:1", "id": "Ticket:1", "summary": "#1 - Free"}]
    params = mock_request.call_args[1]["params"]
    assert params["filter"] == "is_deleted==false"
    assert params["sort"] == "id:desc"


@patch("integrations.itsm.glpi.client.SyncMapping")
@patch("integrations.itsm.glpi.client.requests.request")
def test_list_does_not_offer_an_item_twice_when_pages_shift(mock_request, mock_sync):
    first = [{"id": i, "name": f"T{i}"} for i in range(LIST_PAGE_SIZE + 1, 1, -1)]
    # A ticket created between the two requests pushes #2 onto the next page.
    second = [{"id": 2, "name": "T2"}, {"id": 1, "name": "T1"}]

    results = _list(mock_request, mock_sync, {"limit": 500}, [first, second])

    ids = [r["id"] for r in results]
    assert len(ids) == len(set(ids)) == LIST_PAGE_SIZE + 1
    assert ids[-2:] == ["Ticket:2", "Ticket:1"]


@patch("integrations.itsm.glpi.client.SyncMapping")
@patch("integrations.itsm.glpi.client.requests.request")
def test_list_search_is_quoted_and_cannot_inject_operators(mock_request, mock_sync):
    _list(mock_request, mock_sync, {"search": 'fire";id=gt=0;name=="*'}, [[]])

    assert mock_request.call_args[1]["params"]["filter"] == (
        'is_deleted==false;name=ilike="*fire;id=gt=0;name==*"'
    )


@patch("integrations.itsm.glpi.client.SyncMapping")
@patch("integrations.itsm.glpi.client.requests.request")
def test_list_numeric_search_also_matches_the_id(mock_request, mock_sync):
    _list(mock_request, mock_sync, {"search": "42"}, [[]])

    assert mock_request.call_args[1]["params"]["filter"] == (
        'is_deleted==false;(name=ilike="*42*",id==42)'
    )


@patch("integrations.itsm.glpi.client.SyncMapping")
@patch("integrations.itsm.glpi.client.requests.request")
def test_list_hydration_returns_mapped_items_and_ignores_bad_ids(
    mock_request, mock_sync
):
    results = _list(
        mock_request,
        mock_sync,
        {"id": "5,x;y, Ticket:6,Change:7,Computer:8"},
        [[{"id": 5, "name": "Mapped"}, {"id": 6, "name": "Other"}]],
        mapped=["Ticket:5"],
    )

    # Bare or as stored on a link; ids of other item types are not tickets.
    assert [r["id"] for r in results] == ["Ticket:5", "Ticket:6"]
    assert mock_request.call_args[1]["params"]["filter"] == "id=in=(5,6)"


@patch("integrations.itsm.glpi.client.SyncMapping")
@patch("integrations.itsm.glpi.client.requests.request")
def test_list_pages_past_mapped_items(mock_request, mock_sync):
    first = [{"id": i, "name": f"t{i}"} for i in range(LIST_PAGE_SIZE)]
    results = _list(
        mock_request,
        mock_sync,
        {"limit": 5},
        [first, [{"id": 999, "name": "Free"}]],
        mapped=[f"Ticket:{i}" for i in range(LIST_PAGE_SIZE)],
    )

    assert [r["id"] for r in results] == ["Ticket:999"]
    assert mock_request.call_count == 2
    assert mock_request.call_args[1]["params"]["start"] == LIST_PAGE_SIZE


# --- Webhooks ----------------------------------------------------------------


def _signed_request(body: bytes, secret="whsec", timestamp="1794931150"):
    signature = hmac.new(
        secret.encode(), body + timestamp.encode(), hashlib.sha256
    ).hexdigest()
    request = MagicMock()
    request.body = body
    request.headers = {"X-GLPI-signature": signature, "X-GLPI-timestamp": timestamp}
    return request


def test_webhook_signature_covers_body_and_timestamp():
    orchestrator = GLPIOrchestrator(_configuration())
    body = json.dumps({"event": "update", "item": {"id": 4}}).encode()

    assert orchestrator.validate_webhook_request(_signed_request(body)) is True

    tampered = _signed_request(body)
    tampered.body = body.replace(b"4", b"5")
    assert orchestrator.validate_webhook_request(tampered) is False

    replayed = _signed_request(body)
    replayed.headers["X-GLPI-timestamp"] = "1794939999"
    assert orchestrator.validate_webhook_request(replayed) is False

    assert (
        orchestrator.validate_webhook_request(_signed_request(body, secret="other"))
        is False
    )


def test_webhook_without_signature_or_secret_is_refused():
    body = b"{}"
    unsigned = MagicMock()
    unsigned.body = body
    unsigned.headers = {}
    with pytest.raises(ValueError):
        GLPIOrchestrator(_configuration()).validate_webhook_request(unsigned)
    with pytest.raises(ValueError):
        GLPIOrchestrator(_configuration(webhook_secret="")).validate_webhook_request(
            _signed_request(body)
        )


def _linked_orchestrator(current):
    """An orchestrator whose item is linked, with GLPI answering ``current``
    when the item is read back."""
    orchestrator = GLPIOrchestrator(_configuration())
    orchestrator._linked = MagicMock(return_value=[("applied_control", "Ticket:4")])
    orchestrator._read_current = MagicMock(return_value=current)
    orchestrator._synced_state = MagicMock(return_value=None)
    orchestrator.pull_changes = MagicMock(return_value=True)
    orchestrator._handle_remote_deletion = MagicMock(return_value=True)
    return orchestrator


def test_update_webhook_applies_what_glpi_holds_now():
    delivered = {"id": 4, "name": "Old name", "date_mod": "2026-11-17T16:01:47+00:00"}
    now = {
        "key": "4",
        "fields": {"id": 4, "name": "New name"},
        "updated": "2026-11-17T16:05:00+00:00",
    }
    orchestrator = _linked_orchestrator(now)

    assert orchestrator.extract_webhook_event_type({"event": "update"}) == "update"
    assert orchestrator.handle_webhook_event("update", {"item": delivered}) is True

    # A late, replayed or reordered delivery cannot bring old values back.
    orchestrator.pull_changes.assert_called_once_with("Ticket:4", now)
    orchestrator._read_current.assert_called_once_with("applied_control", "Ticket:4")
    orchestrator._handle_remote_deletion.assert_not_called()


@pytest.mark.parametrize("event", ["update", "delete"])
@pytest.mark.parametrize(
    "current", [None, {"key": "4", "fields": {"id": 4, "is_deleted": True}}]
)
def test_an_item_gone_from_glpi_flags_the_link(event, current):
    """Purged (None) or in the trash, whichever delivery brings the news."""
    orchestrator = _linked_orchestrator(current)

    assert orchestrator.handle_webhook_event(event, {"item": {"id": 4}}) is True

    orchestrator._handle_remote_deletion.assert_called_once_with("Ticket:4")
    orchestrator.pull_changes.assert_not_called()


def test_delete_webhook_for_an_item_that_still_exists_is_ignored():
    """Restored since, or a replayed delivery."""
    orchestrator = _linked_orchestrator({"key": "4", "fields": {"id": 4}})

    assert orchestrator.handle_webhook_event("delete", {"item": {"id": 4}}) is True

    orchestrator._handle_remote_deletion.assert_not_called()
    orchestrator.pull_changes.assert_not_called()


@pytest.mark.parametrize("event", ["update", "delete"])
def test_nothing_is_done_when_glpi_cannot_be_read_back(event):
    from .integration import _UNREACHABLE

    orchestrator = _linked_orchestrator(_UNREACHABLE)
    item = {"id": 4, "name": "Delivered", "date_mod": "2026-11-17T16:05:00+00:00"}

    assert orchestrator.handle_webhook_event(event, {"item": item}) is False

    orchestrator.pull_changes.assert_not_called()
    orchestrator._handle_remote_deletion.assert_not_called()


def test_webhooks_for_other_items_do_not_reach_glpi():
    orchestrator = _linked_orchestrator(None)
    item = {"id": 4, "name": "T"}

    # Items created in GLPI are not imported.
    assert orchestrator.handle_webhook_event("new", {"item": item}) is True
    assert orchestrator.handle_webhook_event("update", {"item": {}}) is False
    assert orchestrator.handle_webhook_event("purge", {"item": item}) is False

    orchestrator._linked.return_value = []
    assert orchestrator.handle_webhook_event("update", {"item": item}) is False
    assert orchestrator.handle_webhook_event("delete", {"item": item}) is False

    orchestrator._read_current.assert_not_called()
    orchestrator.pull_changes.assert_not_called()
    orchestrator._handle_remote_deletion.assert_not_called()


def test_a_ticket_and_an_asset_sharing_an_id_are_each_read_as_their_own_type():
    orchestrator = GLPIOrchestrator(_configuration(ASSET_SETTINGS))
    orchestrator._linked = MagicMock(
        return_value=[("applied_control", "Ticket:4"), ("asset", "Computer:4")]
    )
    ticket = {"key": "4", "fields": {"id": 4, "name": "Ticket"}, "updated": None}
    orchestrator._read_current = MagicMock(
        side_effect=lambda model_key, remote_id: (
            ticket if model_key == "applied_control" else None
        )
    )
    orchestrator._synced_state = MagicMock(return_value=None)
    orchestrator.pull_changes = MagicMock(return_value=True)
    orchestrator._handle_remote_deletion = MagicMock(return_value=True)

    # The computer was purged; ticket 4 is untouched and only re-read.
    assert orchestrator.handle_webhook_event("delete", {"item": {"id": 4}}) is True

    orchestrator._handle_remote_deletion.assert_called_once_with("Computer:4")
    orchestrator.pull_changes.assert_not_called()

    assert orchestrator.handle_webhook_event("update", {"item": {"id": 4}}) is True
    orchestrator.pull_changes.assert_called_once_with("Ticket:4", ticket)


@patch("integrations.itsm.glpi.client.requests.request")
def test_read_item_tells_a_missing_item_from_a_failure(mock_request):
    def answer(status, payload=None):
        response = requests.Response()
        response.status_code = status
        response._content = json.dumps(payload or {}).encode()
        return response

    client = _client()
    client._get_token = MagicMock(return_value="tok")

    mock_request.return_value = answer(200, {"id": 4, "date_mod": "d"})
    assert client.read_item("4") == {
        "key": "4",
        "fields": {"id": 4, "date_mod": "d"},
        "updated": "d",
    }

    assert client.read_item("Ticket:4")["key"] == "4"

    mock_request.return_value = answer(404)
    assert client.read_item("4") is None

    mock_request.return_value = answer(503)
    with pytest.raises(requests.exceptions.HTTPError):
        client.read_item("4")


@patch("integrations.itsm.glpi.client.requests.request")
@patch("integrations.itsm.glpi.client.requests.post")
def test_a_failed_token_request_is_not_a_missing_item(mock_post, mock_request):
    refused = requests.Response()
    refused.status_code = 404
    mock_post.return_value = refused

    with pytest.raises(requests.exceptions.RequestException):
        _client().read_item("4")
    mock_request.assert_not_called()


# Two workers can read the same item back and finish in the other order: a
# state older than the one already synced is not applied.
@pytest.mark.parametrize(
    "synced, read_back, applied",
    [
        ("2026-11-17T16:05:00+00:00", "2026-11-17T16:01:47+00:00", False),
        ("2026-11-17T16:01:47+00:00", "2026-11-17T16:01:47+00:00", True),
        ("2026-11-17T16:01:47+00:00", "2026-11-17T16:05:00+00:00", True),
        (None, "2026-11-17T16:01:47+00:00", True),
        ("2026-11-17T16:05:00+00:00", None, True),
        ("2026-11-17T16:05:00+00:00", "not a date", True),
        ("2026-11-17 16:05:00", "2026-11-17T16:01:47+00:00", True),
    ],
)
def test_a_state_older_than_the_synced_one_is_not_applied(synced, read_back, applied):
    current = {"key": "4", "fields": {"id": 4, "name": "N"}, "updated": read_back}
    orchestrator = _linked_orchestrator(current)
    del orchestrator._synced_state  # the real lookup
    stored = {"key": "4", "fields": {}, "updated": synced} if synced else None

    with patch("integrations.itsm.glpi.integration.SyncMapping") as mapping:
        lookup = mapping.objects.filter.return_value.values_list.return_value
        lookup.first.return_value = stored
        assert orchestrator.handle_webhook_event("update", {"item": {"id": 4}}) is True

    assert orchestrator.pull_changes.called is applied


def _state(name, priority, item_id=4):
    fields = {"id": item_id, "name": name, "priority": priority, "status": {"id": 1}}
    return {"key": str(item_id), "fields": fields, "updated": "d"}


def _merging_orchestrator():
    orchestrator = GLPIOrchestrator(_configuration())
    local_object = MagicMock()
    orchestrator._get_local_object = MagicMock(return_value=local_object)
    orchestrator._update_local_object = MagicMock()
    return orchestrator, local_object


def test_only_what_changed_in_glpi_is_applied():
    """The control was renamed locally and not pushed yet when GLPI reports a
    new priority: only the priority is taken from GLPI."""
    orchestrator, local_object = _merging_orchestrator()
    merge = orchestrator._merge_remote_changes

    mapping = MagicMock(
        remote_data=_state("Old name", 3), version=1, remote_id="Ticket:4"
    )
    assert merge(mapping, _state("Old name", 5), "applied_control") == {"priority": 1}
    orchestrator._update_local_object.assert_called_once_with(
        local_object, {"priority": 1}
    )
    assert mapping.remote_data == _state("Old name", 5)
    mapping.save.assert_called_once()

    # The same delivery again, the rename still not pushed: nothing to apply,
    # so the old name does not come back.
    orchestrator._update_local_object.reset_mock()
    assert merge(mapping, _state("Old name", 5), "applied_control") == {}
    orchestrator._update_local_object.assert_not_called()

    # Both sides changed the same field: GLPI wins.
    assert merge(mapping, _state("Renamed in GLPI", 5), "applied_control") == {
        "name": "Renamed in GLPI"
    }


def test_everything_applies_when_no_state_is_agreed_for_the_item():
    orchestrator, _ = _merging_orchestrator()
    everything = {"name", "priority", "status"}

    mapping = MagicMock(remote_data={}, version=1, remote_id="Ticket:4")
    applied = orchestrator._merge_remote_changes(
        mapping, _state("N", 3), "applied_control"
    )
    assert set(applied) == everything

    # Relinked from ticket 9 to ticket 4: what is stored describes ticket 9.
    mapping = MagicMock(
        remote_data=_state("N", 3, item_id=9), version=1, remote_id="Ticket:4"
    )
    applied = orchestrator._merge_remote_changes(
        mapping, _state("N", 3), "applied_control"
    )
    assert set(applied) == everything


def test_the_state_of_another_item_does_not_date_this_one():
    """A link pointed at another item keeps the old item's state until the
    next sync: its date must not make the new item's look outdated."""
    orchestrator = GLPIOrchestrator(_configuration())
    newer = {"key": "4", "fields": {}, "updated": "2026-11-17T16:05:00+00:00"}
    older = {"key": "5", "fields": {}, "updated": "2026-11-17T16:02:00+00:00"}

    with patch("integrations.itsm.glpi.integration.SyncMapping") as mapping:
        lookup = mapping.objects.filter.return_value.values_list.return_value
        lookup.first.return_value = newer
        assert orchestrator._synced_state("Ticket:5") is None
        assert orchestrator._synced_state("Ticket:4") == newer
    assert orchestrator._is_outdated(None, older) is False
    assert orchestrator._is_outdated(newer, older) is True
