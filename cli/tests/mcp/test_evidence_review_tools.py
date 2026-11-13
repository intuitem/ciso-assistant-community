"""Unit tests for the evidence review MCP tools (mocked HTTP)."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parents[2]))

import base64  # noqa: E402

import pytest  # noqa: E402

from mcp.server.mcpserver import Image  # noqa: E402
from mcp.types import EmbeddedResource  # noqa: E402

from ca_mcp import server  # noqa: E402
from ca_mcp.tools import evidence_review_tools as t  # noqa: E402
from tests.mcp.helpers import UUID_A, UUID_B, UUID_C, _response, run  # noqa: E402

EVIDENCE = {
    "id": UUID_A,
    "name": "Firewall rules",
    "folder": {"str": "Global"},
    "expiry_date": "2027-01-01",
    "requirement_assessments": [{"str": "A.8.20"}],
    "applied_controls": [],
    "latest_revision": {"id": UUID_B, "version": 2, "uploaded_by": "bob@x.io"},
}
REVISIONS = {
    "results": [
        {
            "id": UUID_B,
            "version": 2,
            "attachment": "rules.yaml",
            "attachment_hash": "h2",
            "link": None,
            "review_status": "pending",
            "uploaded_by": {"email": "bob@x.io"},
        },
        {
            "id": UUID_C,
            "version": 1,
            "attachment": "rules.yaml",
            "attachment_hash": "h1",
            "review_status": "approved",
            "reviewed_by": {"email": "ann@x.io"},
            "review_comment": "ok",
        },
    ]
}


@pytest.fixture(autouse=True)
def files_on():
    with (
        patch.object(t.config, "READ_EVIDENCE_FILES", True),
        patch.object(t, "fetch_bytes", return_value=(200, b"allow: 443\n")),
    ):
        yield


def _get():
    def fake(endpoint, params=None):
        if endpoint == f"/evidences/{UUID_A}/":
            return _response(200, EVIDENCE)
        if endpoint == "/evidence-revisions/":
            return _response(200, REVISIONS)
        return _response(200, {"results": [EVIDENCE], "count": 1})

    return fake


def test_tools_registered_read_vs_write():
    assert t.get_evidences_to_review in server.READ_TOOLS
    assert t.read_evidence in server.READ_TOOLS
    assert t.review_evidence in server.WRITE_TOOLS
    assert t.review_evidence not in server.READ_TOOLS


def test_queue_filters_and_rows():
    with (
        patch.object(t, "make_get_request", side_effect=_get()) as get,
        patch.object(t, "resolve_folder_id", return_value=UUID_C),
    ):
        out = run(t.get_evidences_to_review(folder="Global"))
    params = get.call_args.kwargs["params"]
    assert params["review_status"] == "pending"
    assert params["ordering"] == "updated_at"
    assert params["folder"] == UUID_C
    assert "Firewall rules" in out and "v2" in out


def test_queue_rejects_unknown_status():
    assert run(t.get_evidences_to_review(review_status="maybe")).startswith("Error")


def test_read_text_file_and_history():
    with (
        patch.object(t, "make_get_request", side_effect=_get()),
        patch.object(t, "resolve_evidence_id", return_value=UUID_A),
    ):
        out = run(t.read_evidence("Firewall rules"))
    assert "allow: 443" in out and "UNTRUSTED CONTENT" in out
    assert "attachment_hash h2" in out
    assert "ann@x.io" in out and "A.8.20" in out


def test_file_reading_off_by_default_fetches_nothing():
    with (
        patch.object(t.config, "READ_EVIDENCE_FILES", False),
        patch.object(t, "make_get_request", side_effect=_get()),
        patch.object(t, "resolve_evidence_id", return_value=UUID_A),
        patch.object(t, "fetch_bytes") as fetch,
    ):
        out = run(t.read_evidence(UUID_A))
    fetch.assert_not_called()
    assert "CA_MCP_READ_EVIDENCE_FILES" in out and "attachment_hash h2" in out


def test_oversized_file_is_refused():
    with (
        patch.object(t, "make_get_request", side_effect=_get()),
        patch.object(t, "resolve_evidence_id", return_value=UUID_A),
        patch.object(t, "fetch_bytes", return_value=(200, None)),
    ):
        out = run(t.read_evidence(UUID_A))
    assert "over 5 MB" in out


def test_read_image_returns_image_content():
    rev = dict(REVISIONS["results"][0], attachment="shot.png")
    with (
        patch.dict(REVISIONS, {"results": [rev]}),
        patch.object(t, "make_get_request", side_effect=_get()),
        patch.object(t, "fetch_bytes", return_value=(200, b"\x89PNG")),
        patch.object(t, "resolve_evidence_id", return_value=UUID_A),
    ):
        out = run(t.read_evidence(UUID_A))
    assert isinstance(out, list) and isinstance(out[1], Image)


def _read_pdf(tmp_path, is_http):
    rev = dict(REVISIONS["results"][0], attachment="../policy.pdf")
    with (
        patch.dict(REVISIONS, {"results": [rev]}),
        patch.object(t, "make_get_request", side_effect=_get()),
        patch.object(t, "fetch_bytes", return_value=(200, b"%PDF-1.7")),
        patch.object(t, "resolve_evidence_id", return_value=UUID_A),
        patch.object(t.config, "IS_HTTP", is_http),
        patch.object(t, "_DOWNLOAD_DIR", tmp_path),
    ):
        return run(t.read_evidence(UUID_A))


def test_read_pdf_saved_locally_under_stdio(tmp_path):
    out = _read_pdf(tmp_path, is_http=False)
    path = tmp_path / f"{UUID_B}-policy.pdf"  # basename only: no path traversal
    assert path.read_bytes() == b"%PDF-1.7"
    assert str(path) in out


def test_read_pdf_embedded_over_http(tmp_path):
    out = _read_pdf(tmp_path, is_http=True)
    text, extra = out
    assert isinstance(extra, EmbeddedResource)
    assert extra.resource.mime_type == "application/pdf"
    assert base64.b64decode(extra.resource.blob) == b"%PDF-1.7"
    assert "attached" in text
    assert not list(tmp_path.iterdir())


def _review(post_response, **kwargs):
    with (
        patch.object(t, "make_get_request", side_effect=_get()),
        patch.object(t, "make_post_request", return_value=post_response) as post,
        patch.object(t, "resolve_evidence_id", return_value=UUID_A),
    ):
        return run(t.review_evidence(UUID_A, **kwargs)), post


def test_review_posts_seen_content_to_latest_revision():
    out, post = _review(
        _response(200, {"version": 2}), decision="approved", attachment_hash="h2"
    )
    endpoint, payload = post.call_args.args
    assert endpoint == f"/evidence-revisions/{UUID_B}/review/"
    assert payload["seen"] == {"attachment_hash": "h2", "link": None}
    assert "Approved" in out


def test_review_guards_before_any_request():
    for kwargs in (
        {"decision": "maybe", "attachment_hash": "h2"},
        {"decision": "rejected", "attachment_hash": "h2"},
        {"decision": "approved"},
    ):
        out, post = _review(_response(200), **kwargs)
        assert out.startswith("Error")
        post.assert_not_called()


def test_review_stale_and_four_eyes_messages():
    out, _ = _review(_response(409), decision="approved", attachment_hash="h1")
    assert "read_evidence again" in out
    out, _ = _review(
        _response(400, text='{"decision":["four_eyes_uploader_cannot_review"]}'),
        decision="approved",
        attachment_hash="h2",
    )
    assert "four-eyes" in out


def test_fetch_bytes_stops_at_cap():
    from ca_mcp import client

    res = Mock(status_code=200)
    res.__enter__ = Mock(return_value=res)
    res.__exit__ = Mock(return_value=False)
    res.iter_content.return_value = iter([b"a" * 4, b"b" * 4, b"c" * 4])
    with patch.object(client.requests, "get", return_value=res):
        assert client.fetch_bytes("/x/", 6) == (200, None)
    res.iter_content.return_value = iter([b"a" * 4])
    with patch.object(client.requests, "get", return_value=res):
        assert client.fetch_bytes("/x/", 6) == (200, b"aaaa")
