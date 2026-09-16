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
    responses,
    api_url="https://host.test/api",
    endpoint="/folders/",
    params=None,
    **kwargs,
):
    """Run fetch_all_results against canned responses; return (results, error, calls).

    calls is a list of (url, params) actually passed to requests.get.
    API_PATH is derived from API_URL at import time, so patch both.
    """
    api_path = client.urlsplit(api_url).path.rstrip("/")
    with (
        patch.object(client, "API_URL", api_url),
        patch.object(client, "API_PATH", api_path),
        patch.object(client.requests, "get", side_effect=responses) as mock_get,
    ):
        results, error = client.fetch_all_results(endpoint, params=params, **kwargs)
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
        # The "/api" prefix carried by the next link must not be prefixed a
        # second time by make_get_request (the /api/api/... 404 regression).
        assert calls[0][0] == "https://host.test/api/folders/"
        assert calls[1][0] == "https://host.test/api/folders/?limit=1&offset=1"

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
        assert calls[1][1]["offset"] == "1"

    @pytest.mark.unit
    def test_api_url_without_path_prefix(self):
        # With no path on API_URL, the link's /api prefix must be kept.
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
        assert calls[1][0] == "https://host.test/api/folders/?limit=1&offset=1"

    @pytest.mark.unit
    def test_first_request_keeps_caller_params(self):
        responses = [
            _response(json_data={"count": 1, "next": None, "results": [{"id": 1}]}),
        ]
        results, error, calls = _fetch(responses, params={"folder": "abc"})
        assert error is None
        assert calls[0][0] == "https://host.test/api/folders/"
        assert calls[0][1]["folder"] == "abc"

    @pytest.mark.unit
    def test_plain_list_response_is_returned_as_is(self):
        responses = [_response(json_data=[{"id": 1}, {"id": 2}])]
        results, error, calls = _fetch(responses)
        assert error is None
        assert len(results) == 2
        assert len(calls) == 1

    @pytest.mark.unit
    def test_mid_stream_error_returns_partial_and_error(self):
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
        assert error is not None and "500" in error

    @pytest.mark.unit
    def test_max_items_caps_the_walk_with_a_truncation_note(self):
        responses = [
            _response(
                json_data={
                    "count": 10,
                    "next": "/api/folders/?limit=2&offset=2",
                    "results": [{"id": 1}, {"id": 2}],
                }
            ),
        ]
        results, error, calls = _fetch(responses, max_items=2)
        assert error is None
        assert len(results) == 2
        assert len(calls) == 1
        assert results.total == 10
        assert "TRUNCATED" in results.truncation_note
