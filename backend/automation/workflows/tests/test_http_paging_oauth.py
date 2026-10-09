import json
from urllib.parse import parse_qs, urlsplit

import pytest

from automation.workflows.actions import dig, validate_http_request_config
from automation.workflows.engine import start_instance
from automation.workflows.models import WorkflowInstance
from automation.workflows.tests.test_unreachable_tool import fetch_flow, make_domain


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status
        self.text = json.dumps(payload)

    def json(self):
        return self.payload


@pytest.fixture
def tool(monkeypatch):
    monkeypatch.setattr(
        "core.net_safety.assert_public_url_unless_dev", lambda *a, **k: None
    )
    calls = {"requests": [], "tokens": []}
    pages = {}

    def request(method, url, **kwargs):
        calls["requests"].append({"url": url, "headers": kwargs.get("headers")})
        return pages["handler"](url)

    def post(url, **kwargs):
        calls["tokens"].append({"url": url, "data": kwargs.get("data")})
        return pages.get("token", FakeResponse({"access_token": "tok-123"}))

    monkeypatch.setattr("requests.request", request)
    monkeypatch.setattr("requests.post", post)
    calls["pages"] = pages
    return calls


def output(instance):
    instance.refresh_from_db()
    return instance.node_outputs["pull"]


def graph_pages(url):
    if "skiptoken" not in url:
        return FakeResponse(
            {
                "value": [{"id": 1}, {"id": 2}],
                "@odata.nextLink": "https://tool.invalid/coverage.json?skiptoken=2",
            }
        )
    return FakeResponse({"value": [{"id": 3}]})


def cursor_pages(url):
    cursor = parse_qs(urlsplit(url).query).get("cursor", [None])[0]
    if cursor is None:
        return FakeResponse({"data": [{"id": "a"}], "pagination": {"nextCursor": "c2"}})
    return FakeResponse({"data": [{"id": "b"}], "pagination": {"nextCursor": None}})


@pytest.mark.django_db
class TestPaging:
    def test_follows_next_links_and_gathers_items(self, tool):
        tool["pages"]["handler"] = graph_pages
        instance = start_instance(
            fetch_flow(
                make_domain("Graph"),
                paginate={"items": "value", "next": "@odata.nextLink"},
            )
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED
        result = output(instance)
        assert [item["id"] for item in result["items"]] == [1, 2, 3]
        assert result["pages"] == 2
        assert result["truncated"] is False
        assert result["body"] is None

    def test_cursor_goes_into_the_query_string(self, tool):
        tool["pages"]["handler"] = cursor_pages
        instance = start_instance(
            fetch_flow(
                make_domain("Cursor"),
                url="https://tool.invalid/agents?limit=1",
                paginate={
                    "items": "data",
                    "next": "pagination.nextCursor",
                    "cursor_param": "cursor",
                },
            )
        )
        result = output(instance)
        assert [item["id"] for item in result["items"]] == ["a", "b"]
        second = parse_qs(urlsplit(tool["requests"][1]["url"]).query)
        assert second == {"limit": ["1"], "cursor": ["c2"]}

    def test_page_limit_marks_the_result_truncated(self, tool):
        tool["pages"]["handler"] = graph_pages
        instance = start_instance(
            fetch_flow(
                make_domain("Capped"),
                paginate={"items": "value", "next": "@odata.nextLink", "max_pages": 1},
            )
        )
        result = output(instance)
        assert len(result["items"]) == 2
        assert result["truncated"] is True

    def test_item_cap_truncates(self, tool, settings):
        settings.WORKFLOW_HTTP_MAX_ITEMS = 1
        tool["pages"]["handler"] = graph_pages
        instance = start_instance(
            fetch_flow(
                make_domain("Items"),
                paginate={"items": "value", "next": "@odata.nextLink"},
            )
        )
        result = output(instance)
        assert len(result["items"]) == 1
        assert result["truncated"] is True
        assert len(tool["requests"]) == 1

    def test_output_budget_stops_paging(self, tool, settings):
        settings.WORKFLOW_NODE_OUTPUT_BUDGET = 1200
        tool["pages"]["handler"] = lambda url: FakeResponse(
            {"value": [{"blob": "x" * 400} for _ in range(3)]}
        )
        instance = start_instance(
            fetch_flow(
                make_domain("Budget"),
                paginate={"items": "value", "next": "@odata.nextLink"},
            )
        )
        result = output(instance)
        assert result["count"] == len(result["items"]) == 2
        assert result["truncated"] is True

    def test_a_next_link_to_another_host_fails(self, tool):
        tool["pages"]["handler"] = lambda url: FakeResponse(
            {"value": [], "@odata.nextLink": "https://elsewhere.invalid/steal"}
        )
        instance = start_instance(
            fetch_flow(
                make_domain("Away"),
                paginate={"items": "value", "next": "@odata.nextLink"},
            )
        )
        assert instance.status == WorkflowInstance.Status.FAILED
        assert len(tool["requests"]) == 1

    def test_a_next_link_that_repeats_fails(self, tool):
        tool["pages"]["handler"] = lambda url: FakeResponse(
            {
                "value": [{"id": 1}],
                "@odata.nextLink": "https://tool.invalid/coverage.json?skiptoken=1",
            }
        )
        instance = start_instance(
            fetch_flow(
                make_domain("Loop"),
                paginate={"items": "value", "next": "@odata.nextLink"},
            )
        )
        assert instance.status == WorkflowInstance.Status.FAILED
        assert len(tool["requests"]) == 2

    def test_a_cursor_that_repeats_fails(self, tool):
        tool["pages"]["handler"] = lambda url: FakeResponse(
            {"data": [{"id": "a"}], "pagination": {"nextCursor": "same"}}
        )
        instance = start_instance(
            fetch_flow(
                make_domain("CursorLoop"),
                paginate={
                    "items": "data",
                    "next": "pagination.nextCursor",
                    "cursor_param": "cursor",
                },
            )
        )
        assert instance.status == WorkflowInstance.Status.FAILED
        assert len(tool["requests"]) == 2

    def test_a_missing_items_list_fails(self, tool):
        tool["pages"]["handler"] = lambda url: FakeResponse({"other": []})
        instance = start_instance(
            fetch_flow(
                make_domain("NoItems"),
                paginate={"items": "value", "next": "@odata.nextLink"},
            )
        )
        assert instance.status == WorkflowInstance.Status.FAILED

    def test_without_paging_the_output_keeps_its_shape(self, tool):
        tool["pages"]["handler"] = lambda url: FakeResponse({"value": 7})
        instance = start_instance(fetch_flow(make_domain("Plain")))
        result = output(instance)
        assert result["body"] == {"value": 7}
        assert result["items"] is None


OAUTH = {
    "token_url": "https://login.invalid/tenant/oauth2/v2.0/token",
    "client_id": "app",
    "client_secret": "s3cret",
    "scope": "https://graph.invalid/.default",
}


def offset_pages(url):
    skip = int(parse_qs(urlsplit(url).query).get("$skip", ["0"])[0])
    rows = [{"id": i} for i in range(5)]
    return FakeResponse({"value": rows[skip : skip + 2]})


@pytest.mark.django_db
class TestOffsetPaging:
    def test_skips_by_page_size_until_a_short_page(self, tool):
        tool["pages"]["handler"] = offset_pages
        result = output(
            start_instance(
                fetch_flow(
                    make_domain("Offset"),
                    url="https://tool.invalid/machines?$top=2",
                    paginate={
                        "items": "value",
                        "offset_param": "$skip",
                        "page_size": 2,
                    },
                )
            )
        )
        assert [item["id"] for item in result["items"]] == [0, 1, 2, 3, 4]
        assert result["count"] == 5
        skips = [
            parse_qs(urlsplit(call["url"]).query).get("$skip")
            for call in tool["requests"]
        ]
        assert skips == [None, ["2"], ["4"]]

    def test_page_limit_truncates(self, tool):
        tool["pages"]["handler"] = offset_pages
        result = output(
            start_instance(
                fetch_flow(
                    make_domain("OffsetCap"),
                    paginate={
                        "items": "value",
                        "offset_param": "$skip",
                        "page_size": 2,
                        "max_pages": 2,
                    },
                )
            )
        )
        assert result["count"] == 4
        assert result["truncated"] is True

    def test_offset_paging_without_a_page_size_fails(self, tool):
        tool["pages"]["handler"] = offset_pages
        instance = start_instance(
            fetch_flow(
                make_domain("NoSize"),
                paginate={"items": "value", "offset_param": "$skip"},
            )
        )
        assert instance.status == WorkflowInstance.Status.FAILED
        assert tool["requests"] == []

    def test_count_only_keeps_no_items(self, tool):
        tool["pages"]["handler"] = graph_pages
        result = output(
            start_instance(
                fetch_flow(
                    make_domain("CountOnly"),
                    paginate={
                        "items": "value",
                        "next": "@odata.nextLink",
                        "count_only": True,
                    },
                )
            )
        )
        assert result["count"] == 3
        assert result["items"] is None


@pytest.mark.django_db
class TestOAuth:
    def test_token_is_fetched_and_sent_as_bearer(self, tool):
        tool["pages"]["handler"] = lambda url: FakeResponse({"value": 1})
        instance = start_instance(fetch_flow(make_domain("OAuth"), oauth=OAUTH))
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert tool["tokens"][0]["data"] == {
            "grant_type": "client_credentials",
            "client_id": "app",
            "client_secret": "s3cret",
            "scope": "https://graph.invalid/.default",
        }
        assert tool["requests"][0]["headers"]["Authorization"] == "Bearer tok-123"

    def test_the_token_is_not_persisted(self, tool):
        tool["pages"]["handler"] = lambda url: FakeResponse({"value": 1})
        instance = start_instance(fetch_flow(make_domain("Quiet"), oauth=OAUTH))
        instance.refresh_from_db()
        assert "tok-123" not in json.dumps(instance.node_outputs)
        assert "tok-123" not in json.dumps(instance.variables)

    def test_a_refused_token_fails_the_run(self, tool):
        tool["pages"]["token"] = FakeResponse({"error": "invalid_client"}, 401)
        tool["pages"]["handler"] = lambda url: FakeResponse({"value": 1})
        instance = start_instance(fetch_flow(make_domain("Refused"), oauth=OAUTH))
        assert instance.status == WorkflowInstance.Status.FAILED
        assert tool["requests"] == []

    def test_a_cleartext_token_url_fails(self, tool):
        tool["pages"]["handler"] = lambda url: FakeResponse({"value": 1})
        instance = start_instance(
            fetch_flow(
                make_domain("Cleartext"),
                oauth={**OAUTH, "token_url": "http://login.invalid/token"},
            )
        )
        assert instance.status == WorkflowInstance.Status.FAILED
        assert tool["tokens"] == []


class TestDottedKeys:
    def test_a_key_with_dots_resolves_whole(self):
        assert dig({"body": {"@odata.count": 4}}, "body.@odata.count") == 4

    def test_plain_paths_are_unchanged(self):
        assert dig({"a": {"b": [{"c": 1}]}}, "a.b.0.c") == 1
        assert dig({"a": {}}, "a.b", "none") == "none"


def http_node(**config):
    return type(
        "Node",
        (),
        {
            "action_config": {
                "type": "http_request",
                "url": "https://tool.invalid/x",
                **config,
            }
        },
    )()


class TestPublishChecks:
    def codes(self, **config):
        return {code for code, _ in validate_http_request_config(http_node(**config))}

    def test_valid_settings_pass(self):
        assert (
            self.codes(
                oauth=OAUTH,
                paginate={"items": "value", "next": "@odata.nextLink", "max_pages": 5},
            )
            == set()
        )

    def test_incomplete_oauth(self):
        assert "action_http_oauth_missing" in self.codes(
            oauth={"token_url": "https://login.invalid/token"}
        )

    def test_cleartext_token_url(self):
        assert "action_http_credentials_need_https" in self.codes(
            oauth={**OAUTH, "token_url": "http://login.invalid/token"}
        )

    def test_oauth_needs_an_https_target(self):
        assert "action_http_credentials_need_https" in self.codes(
            url="http://tool.invalid/x", oauth=OAUTH
        )

    def test_incomplete_paging(self):
        assert "action_http_paginate_missing" in self.codes(paginate={"items": "value"})

    def test_offset_paging_needs_a_page_size(self):
        assert "action_http_bad_page_size" in self.codes(
            paginate={"items": "value", "offset_param": "$skip"}
        )

    def test_offset_paging_needs_no_next_path(self):
        assert (
            self.codes(
                paginate={"items": "value", "offset_param": "$skip", "page_size": 100}
            )
            == set()
        )

    def test_page_limit_out_of_range(self):
        assert "action_http_bad_max_pages" in self.codes(
            paginate={"items": "value", "next": "n", "max_pages": 500}
        )

    def test_bad_shapes(self):
        codes = self.codes(oauth="x", paginate="y")
        assert {"action_http_bad_oauth", "action_http_bad_paginate"} <= codes
