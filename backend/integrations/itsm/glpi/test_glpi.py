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
            "Computer": {"properties": {"name": {"type": "string"}}},
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


def _client(settings=None):
    with patch("integrations.itsm.glpi.client.check_integration_url"):
        return GLPIClient(_configuration(settings))


def _response(payload=None, status=200):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload
    return response


def _token_response(token="tok", expires_in=3600):
    return _response({"access_token": token, "expires_in": expires_in})


# --- Schema ------------------------------------------------------------------


def test_parse_schema_keeps_assistance_types_and_mappable_properties():
    tables, columns, choices = parse_schema(OPENAPI)

    assert tables == [{"name": "Ticket", "label": "Tickets"}]
    by_name = {c["name"]: c for c in columns["Ticket"]}
    # Scalars and the enum-backed status dropdown; no free dropdowns or arrays.
    assert set(by_name) == {
        "id",
        "name",
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
        "status": 2,
        "priority": 5,
        "resolution_date": "2026-12-24",
    }


@pytest.mark.parametrize(
    "item_type, payload",
    [("Ticket", {"status": 2}), ("Problem", {"status": 2}), ("Change", {})],
)
def test_default_status_only_uses_values_the_item_type_has(item_type, payload):
    mapper = GLPIFieldMapper(_configuration({"table_name": item_type}))
    control = SimpleNamespace(status="in_progress")

    assert mapper.to_remote_partial(control, ["status"]) == payload
    # The statuses every type shares are still sent.
    assert mapper.to_remote_partial(SimpleNamespace(status="on_hold"), ["status"]) == {
        "status": 4
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

    assert mapper.to_remote(SimpleNamespace(status="deprecated")) == {"status": 6}
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
        ({"models": {"asset": {"table_name": "Ticket"}}}, True),
        ({"models": [{}]}, True),
        ({"models": {"applied_control": True}}, True),
    ],
)
def test_settings_are_checked_before_a_configuration_is_created(settings, refused):
    assert bool(GLPIOrchestrator.settings_errors(None, settings)) is refused


def test_only_applied_controls_get_a_client_or_a_mapper():
    orchestrator = GLPIOrchestrator(_configuration())
    with pytest.raises(ValueError):
        orchestrator.mapper_for("asset")
    with pytest.raises(ValueError):
        orchestrator.client_for("asset")
    assert isinstance(orchestrator.mapper_for("applied_control"), GLPIFieldMapper)


def test_item_type_and_ids_cannot_alter_the_request_path():
    with pytest.raises(ValueError):
        _client({"table_name": "../Setup/Webhook"})._collection_path()
    with pytest.raises(ValueError):
        _client()._item_path("3/../../Session")


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
        mapped=["2"],
    )

    assert results == [{"key": "1", "id": "1", "summary": "#1 - Free"}]
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
    assert ids[-2:] == ["2", "1"]


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
        {"id": "5,x;y,6"},
        [[{"id": 5, "name": "Mapped"}, {"id": 6, "name": "Other"}]],
        mapped=["5"],
    )

    assert [r["id"] for r in results] == ["5", "6"]
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
        mapped=[str(i) for i in range(LIST_PAGE_SIZE)],
    )

    assert [r["id"] for r in results] == ["999"]
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
    orchestrator._is_linked = MagicMock(return_value=True)
    orchestrator._read_current = MagicMock(return_value=current)
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
    orchestrator.pull_changes.assert_called_once_with("4", now)


def test_delete_webhook_is_checked_against_glpi():
    item = {"id": 4, "name": "T"}

    # Trashed or purged: the link is flagged.
    for current in ({"key": "4", "fields": {"id": 4, "is_deleted": True}}, None):
        orchestrator = _linked_orchestrator(current)
        assert orchestrator.handle_webhook_event("delete", {"item": item}) is True
        orchestrator._handle_remote_deletion.assert_called_once_with("4")

    # Still there (restored since, or a replayed delivery): nothing to flag.
    orchestrator = _linked_orchestrator({"key": "4", "fields": {"id": 4}})
    assert orchestrator.handle_webhook_event("delete", {"item": item}) is True
    orchestrator._handle_remote_deletion.assert_not_called()


def test_webhooks_for_other_items_do_not_reach_glpi():
    orchestrator = _linked_orchestrator(None)
    item = {"id": 4, "name": "T"}

    # Items created in GLPI are not imported.
    assert orchestrator.handle_webhook_event("new", {"item": item}) is True
    assert orchestrator.handle_webhook_event("update", {"item": {}}) is False
    assert orchestrator.handle_webhook_event("purge", {"item": item}) is False

    orchestrator._is_linked.return_value = False
    assert orchestrator.handle_webhook_event("update", {"item": item}) is False
    assert orchestrator.handle_webhook_event("delete", {"item": item}) is False

    orchestrator._read_current.assert_not_called()
    orchestrator.pull_changes.assert_not_called()
    orchestrator._handle_remote_deletion.assert_not_called()


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

    mock_request.return_value = answer(404)
    assert client.read_item("4") is None

    mock_request.return_value = answer(503)
    with pytest.raises(requests.exceptions.HTTPError):
        client.read_item("4")


# When GLPI cannot be read back, the delivery is all there is: it is applied
# unless it is older than what was already synced.
@pytest.mark.parametrize(
    "synced, incoming, applied",
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
def test_unreadable_item_falls_back_to_the_delivery(synced, incoming, applied):
    from .integration import _UNREACHABLE

    orchestrator = _linked_orchestrator(_UNREACHABLE)
    item = {"id": 4, "name": "Old name", "date_mod": incoming}
    stored = {"key": "4", "fields": {}, "updated": synced} if synced else None

    with patch("integrations.itsm.glpi.integration.SyncMapping") as mapping:
        lookup = mapping.objects.filter.return_value.values_list.return_value
        lookup.first.return_value = stored
        assert orchestrator.handle_webhook_event("update", {"item": item}) is True

    assert orchestrator.pull_changes.called is applied
