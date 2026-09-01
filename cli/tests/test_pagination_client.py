"""Unit tests for fetch_all_results pagination handling.

The backend returns path-relative ``next`` links that include the "/api"
prefix already present in API_URL; these tests assert the exact URLs
requested so a double-prefix regression ("/api/api/...") fails loudly.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from ca_mcp import client  # noqa: E402


def _response(status_code=200, json_data=None, text=""):
    res = Mock()
    res.status_code = status_code
    res.json.return_value = json_data
    res.text = text
    return res


def _fetch(
    responses, api_url="https://host.test/api", endpoint="/folders/", params=None
):
    """Run fetch_all_results against canned responses; return (results, error, calls).

    calls is a list of (url, params) actually passed to requests.get.
    """
    with (
        patch.object(client, "API_URL", api_url),
        patch.object(client.requests, "get", side_effect=responses) as mock_get,
    ):
        results, error = client.fetch_all_results(endpoint, params=params)
    calls = [(c.args[0], c.kwargs.get("params")) for c in mock_get.call_args_list]
    return results, error, calls


class TestFetchAllResults:
    @pytest.mark.unit
    def test_follows_path_relative_next_links(self):
        responses = [
            _response(
                json_data={
                    "count": 2,
                    "next": "/api/folders/?limit=1&offset=1",
                    "results": [{"id": 1}],
                }
            ),
            _response(json_data={"count": 2, "next": None, "results": [{"id": 2}]}),
        ]
        results, error, calls = _fetch(responses)
        assert error is None
        assert [r["id"] for r in results] == [1, 2]
        assert [url for url, _ in calls] == [
            "https://host.test/api/folders/",
            "https://host.test/api/folders/",
        ]
        assert calls[1][1] == {"limit": "1", "offset": "1"}

    @pytest.mark.unit
    def test_follows_absolute_next_links(self):
        responses = [
            _response(
                json_data={
                    "count": 2,
                    "next": "https://host.test/api/folders/?limit=1&offset=1",
                    "results": [{"id": 1}],
                }
            ),
            _response(json_data={"count": 2, "next": None, "results": [{"id": 2}]}),
        ]
        results, error, calls = _fetch(responses)
        assert error is None
        assert [r["id"] for r in results] == [1, 2]
        assert calls[1][0] == "https://host.test/api/folders/"
        assert calls[1][1] == {"limit": "1", "offset": "1"}

    @pytest.mark.unit
    def test_api_url_without_path_prefix(self):
        responses = [
            _response(
                json_data={
                    "count": 2,
                    "next": "/api/folders/?limit=1&offset=1",
                    "results": [{"id": 1}],
                }
            ),
            _response(json_data={"count": 2, "next": None, "results": [{"id": 2}]}),
        ]
        results, error, calls = _fetch(responses, api_url="https://host.test")
        assert error is None
        assert calls[1][0] == "https://host.test/api/folders/"

    @pytest.mark.unit
    def test_first_request_keeps_caller_params(self):
        responses = [
            _response(json_data={"count": 1, "next": None, "results": [{"id": 1}]}),
        ]
        results, error, calls = _fetch(responses, params={"folder": "abc"})
        assert error is None
        assert calls[0] == ("https://host.test/api/folders/", {"folder": "abc"})

    @pytest.mark.unit
    def test_plain_list_response_is_returned_as_is(self):
        responses = [_response(json_data=[{"id": 1}, {"id": 2}])]
        results, error, calls = _fetch(responses)
        assert error is None
        assert len(results) == 2
        assert len(calls) == 1

    @pytest.mark.unit
    def test_mid_stream_error_returns_partial_and_structured_error(self):
        responses = [
            _response(
                json_data={
                    "count": 2,
                    "next": "/api/folders/?limit=1&offset=1",
                    "results": [{"id": 1}],
                }
            ),
            _response(status_code=500, text="boom"),
        ]
        results, error, calls = _fetch(responses)
        assert [r["id"] for r in results] == [1]
        assert error is not None
        # Structured http_error_response, not a bare "Error: HTTP ..." string.
        assert "Error: HTTP 500 - boom" != error


class TestNextLinkToRequest:
    @pytest.mark.unit
    def test_strips_api_prefix_only_on_segment_boundary(self):
        with patch.object(client, "API_URL", "https://host.test/api"):
            path, params = client._next_link_to_request("/api/folders/?offset=5")
            assert path == "/folders/"
            assert params == {"offset": "5"}
            # "/apifolders" is not under the "/api" prefix.
            path, _ = client._next_link_to_request("/apifolders/")
            assert path == "/apifolders/"

    @pytest.mark.unit
    def test_multi_value_query_params_are_preserved(self):
        with patch.object(client, "API_URL", "https://host.test/api"):
            _, params = client._next_link_to_request("/api/x/?a=1&a=2&b=3")
            assert params == {"a": ["1", "2"], "b": "3"}
