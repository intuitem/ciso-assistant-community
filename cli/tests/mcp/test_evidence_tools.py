"""Unit tests for the MCP create_evidence tool and the raw-body upload helper.

Network calls are mocked at their import sites, as in
test_risk_review_tools.py; files are real, under pytest's tmp_path.
"""

import asyncio
import shlex
import sys
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import client  # noqa: E402
from ca_mcp import server  # noqa: E402
from ca_mcp.tools import write_tools  # noqa: E402
from tests.mcp.helpers import (  # noqa: E402
    UUID_A,
    UUID_B,
    UUID_F,
    _response,
    run,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24


class _Mocks:
    """Patch every network entry point of create_evidence at once."""

    def __init__(self, create=None, upload=None, check=None):
        self.create = create or _response(201, {"id": UUID_A, "name": "Alert"})
        self.upload = upload or _response(200)
        self.check = check or _response(200, {"attachment": "/media/alert.png"})
        self.sent = []

    def _send(self, endpoint, filename, f):
        self.sent.append(f.read())
        return self.upload

    def __enter__(self):
        self._patches = [
            patch.object(write_tools, "GLOBAL_FOLDER_ID", None),
            patch.object(write_tools, "resolve_folder_id", return_value=UUID_F),
            patch.object(write_tools, "make_post_request", return_value=self.create),
            patch.object(write_tools, "make_upload_request", side_effect=self._send),
            patch.object(
                write_tools, "make_delete_request", return_value=_response(204)
            ),
            patch.object(write_tools, "make_get_request", return_value=self.check),
        ]
        mocks = [p.__enter__() for p in self._patches]
        self.resolve, self.post, self.up, self.delete, self.get = mocks[1:]
        return self

    def __exit__(self, *exc):
        for p in reversed(self._patches):
            p.__exit__(*exc)

    def assert_no_request(self):
        self.post.assert_not_called()
        self.up.assert_not_called()
        self.delete.assert_not_called()


def _file(tmp_path, name, data=PNG_BYTES):
    path = tmp_path / name
    path.write_bytes(data)
    return path


class TestCreateEvidence:
    def test_nominal(self, tmp_path):
        path = _file(tmp_path, "alert.pdf", b"%PDF-1.4" + b"x" * 1992)
        with _Mocks() as m:
            out = run(
                write_tools.create_evidence(
                    file_path=str(path),
                    name="Alert",
                    folder_id="SOC",
                    description="SIEM alert",
                )
            )
        m.resolve.assert_called_once_with("SOC")
        assert m.post.call_args.args == (
            "/evidences/",
            {"name": "Alert", "folder": UUID_F, "description": "SIEM alert"},
        )
        assert m.up.call_args.args[:2] == (f"/evidences/{UUID_A}/upload/", "alert.pdf")
        assert m.sent == [path.read_bytes()]
        m.get.assert_called_once_with(f"/evidences/{UUID_A}/")
        m.delete.assert_not_called()
        assert out == (
            f"Created evidence: Alert (ID: {UUID_A}) with attachment alert.pdf (2.0 KB)"
        )

    def test_default_name_is_file_name(self, tmp_path):
        path = _file(tmp_path, "alert.png")
        with _Mocks() as m:
            run(write_tools.create_evidence(file_path=str(path)))
        assert m.post.call_args.args[1] == {"name": "alert.png"}

    def test_tilde_is_expanded(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        (tmp_path / "Pictures").mkdir()
        _file(tmp_path / "Pictures", "a.png")
        with _Mocks() as m:
            out = run(write_tools.create_evidence(file_path="~/Pictures/a.png"))
        assert out.startswith("Created evidence:")
        assert m.up.call_args.args[1] == "a.png"
        assert m.sent == [PNG_BYTES]

    def test_non_ascii_name_is_passed_through(self, tmp_path):
        path = _file(tmp_path, "alerte-été.png")
        with _Mocks() as m:
            run(write_tools.create_evidence(file_path=str(path)))
        assert m.up.call_args.args[1] == "alerte-été.png"

    def test_missing_file(self, tmp_path):
        missing = str(tmp_path / "nope.png")
        with _Mocks() as m:
            out = run(write_tools.create_evidence(file_path=missing))
        assert out == f"Error: file not found: {missing}"
        m.assert_no_request()

    def test_hidden_paths_are_refused(self, tmp_path):
        (tmp_path / ".docker").mkdir()
        for name in (".docker/config.json", ".env.json"):
            path = _file(tmp_path, name)
            with _Mocks() as m:
                out = run(write_tools.create_evidence(file_path=str(path)))
            assert out == f"Error: refusing a hidden file or directory: {path}"
            m.assert_no_request()

    def test_symlink_to_hidden_file_is_refused(self, tmp_path):
        (tmp_path / ".ssh").mkdir()
        link = tmp_path / "key.txt"
        link.symlink_to(_file(tmp_path, ".ssh/id_rsa.txt"))
        with _Mocks() as m:
            out = run(write_tools.create_evidence(file_path=str(link)))
        assert out.startswith("Error: refusing a hidden file or directory:")
        m.assert_no_request()

    def test_directory_is_not_a_file(self, tmp_path):
        folder = tmp_path / "shots.png"
        folder.mkdir()
        with _Mocks() as m:
            out = run(write_tools.create_evidence(file_path=str(folder)))
        assert out == f"Error: file not found: {folder}"
        m.assert_no_request()

    def test_create_rejected(self, tmp_path):
        path = _file(tmp_path, "alert.png")
        rejected = _response(400, text='{"name":["already exists"]}')
        with _Mocks(create=rejected) as m:
            out = run(write_tools.create_evidence(file_path=str(path)))
        assert out == 'Error creating evidence: 400 - {"name":["already exists"]}'
        m.up.assert_not_called()
        m.delete.assert_not_called()

    def test_upload_rejected_deletes_evidence(self, tmp_path):
        path = _file(tmp_path, "alert.png")
        rejected = _response(400, text='{"detail":"too large"}')
        with _Mocks(upload=rejected) as m:
            out = run(write_tools.create_evidence(file_path=str(path)))
        assert out == 'Error uploading attachment: 400 - {"detail":"too large"}'
        m.delete.assert_called_once_with(f"/evidences/{UUID_A}/")

    def test_upload_ok_but_nothing_stored_deletes_evidence(self, tmp_path):
        path = _file(tmp_path, "alert.png")
        with _Mocks(check=_response(200, {"attachment": None})) as m:
            out = run(write_tools.create_evidence(file_path=str(path)))
        assert out == "Error uploading attachment: the server stored no file"
        m.delete.assert_called_once_with(f"/evidences/{UUID_A}/")

    def test_upload_ok_but_unverifiable_is_success(self, tmp_path):
        path = _file(tmp_path, "alert.png")
        with _Mocks(check=_response(500)) as m:
            out = run(write_tools.create_evidence(file_path=str(path)))
        assert out.startswith("Created evidence:")
        m.delete.assert_not_called()

    def _upload_raises(self, tmp_path, check):
        """Upload raises; `check` is the GET /evidences/<id>/ outcome."""
        path = _file(tmp_path, "alert.png")
        get = (
            {"side_effect": check}
            if isinstance(check, Exception)
            else {"return_value": check}
        )
        with (
            _Mocks() as m,
            patch.object(write_tools, "make_get_request", **get) as g,
        ):
            m.up.side_effect = TimeoutError("read timed out")
            out = run(write_tools.create_evidence(file_path=str(path)))
        g.assert_called_once_with(f"/evidences/{UUID_A}/")
        return out, m

    def test_upload_exception_but_file_stored_is_success(self, tmp_path):
        stored = _response(200, {"id": UUID_A, "attachment": "/media/alert.png"})
        out, m = self._upload_raises(tmp_path, stored)
        assert out.startswith(f"Created evidence: Alert (ID: {UUID_A})")
        m.delete.assert_not_called()

    def test_upload_exception_without_file_keeps_evidence(self, tmp_path):
        for check in (
            _response(200, {"id": UUID_A, "attachment": None}),
            ConnectionError("unreachable"),
        ):
            out, m = self._upload_raises(tmp_path, check)
            assert out == (
                "Error uploading attachment, outcome unknown: read timed out "
                f"(evidence {UUID_A} kept: check it before retrying)"
            )
            m.delete.assert_not_called()

    def test_empty_file_is_refused(self, tmp_path):
        path = _file(tmp_path, "blank.png", b"")
        with _Mocks() as m:
            out = run(write_tools.create_evidence(file_path=str(path)))
        assert out == f"Error: file is empty: {path}"
        m.assert_no_request()

    def test_unreadable_file_creates_no_evidence(self, tmp_path):
        path = _file(tmp_path, "alert.png")
        with (
            _Mocks() as m,
            patch.object(Path, "open", side_effect=PermissionError("denied")),
        ):
            out = run(write_tools.create_evidence(file_path=str(path)))
        assert out == "Error in create_evidence: denied"
        m.assert_no_request()

    def test_failed_rollback_is_reported(self, tmp_path):
        path = _file(tmp_path, "alert.png")
        rejected = _response(400, text="too large")
        with _Mocks(upload=rejected) as m:
            m.delete.return_value = _response(500)
            out = run(write_tools.create_evidence(file_path=str(path)))
        assert out == (
            "Error uploading attachment: 400 - too large"
            f" (could not delete empty evidence {UUID_A}, remove it manually)"
        )


class TestMakeUploadRequest:
    def test_raw_body_and_content_disposition(self):
        with (
            patch.object(client, "get_request_token", return_value="tok"),
            patch.object(client, "API_URL", "https://ca.test/api"),
            patch.object(client.requests, "post", return_value=_response()) as post,
        ):
            client.make_upload_request(
                f"/evidences/{UUID_A}/upload/", 'alerte "été";.png', b"bytes"
            )
        args, kwargs = post.call_args
        assert args == (f"https://ca.test/api/evidences/{UUID_A}/upload/",)
        assert kwargs["data"] == b"bytes"
        assert "json" not in kwargs and "files" not in kwargs
        assert kwargs["headers"]["Authorization"] == "Token tok"
        assert "Content-Type" not in kwargs["headers"]
        header = kwargs["headers"]["Content-Disposition"]
        assert header == (
            'attachment; filename="alerte --t---.png"; '
            "filename*=utf-8''alerte%20%22%C3%A9t%C3%A9%22%3B.png"
        )
        header.encode("latin-1")  # must be a valid header value
        assert kwargs["verify"] == client.VERIFY_CERTIFICATE
        assert kwargs["timeout"] == client.HTTP_TIMEOUT


class TestContentDispositionHeader:
    def test_unsafe_characters_are_neutralised(self):
        header = client.content_disposition_header('a\r\nb\\c%d"e.png')
        ascii_part = header.split("; filename*=")[0]
        assert ascii_part == 'attachment; filename="a--b-c-d-e.png"'
        filename = ascii_part.split("filename=")[1].strip('"')
        for char in ("\r", "\n", "\\", "%", '"'):
            assert char not in filename
        assert header.endswith("filename*=utf-8''a%0D%0Ab%5Cc%25d%22e.png")

    def test_all_non_ascii_stem(self):
        assert client.content_disposition_header("été.png") == (
            "attachment; filename=\"-t-.png\"; filename*=utf-8''%C3%A9t%C3%A9.png"
        )


def test_create_evidence_is_a_write_tool():
    assert write_tools.create_evidence in server.WRITE_TOOLS
    assert write_tools.create_evidence not in server.READ_TOOLS


def test_create_evidence_is_not_registered_over_http():
    from mcp.server.mcpserver import MCPServer

    def names(is_http):
        fresh = MCPServer("test")
        with (
            patch.object(server, "mcp", fresh),
            patch.object(server, "_registered", False),
            patch.object(server.config, "IS_HTTP", is_http),
        ):
            server.register_tools(read_only=False)
            return {t.name for t in asyncio.run(fresh.list_tools())}

    assert "create_evidence" in names(False)
    assert "create_evidence" not in names(True)


# ---------------------------------------------------------------------------
# prepare_evidence_upload (remote: the client curls the file itself)
# ---------------------------------------------------------------------------

UPLOAD_URL = "https://ca.example.com/api/evidences/upload/tok.en:sig/"
ISSUED = {"url": UPLOAD_URL, "expires_at": "2026-11-20T10:15:00+00:00"}


class TestPrepareEvidenceUpload:
    def _post(self, *responses):
        sent = []
        queue = list(responses)

        def fake(endpoint, payload):
            sent.append((endpoint, payload))
            return queue.pop(0)

        fake.sent = sent
        return fake

    def _patches(self, post, delete=None):
        return (
            patch.object(write_tools, "GLOBAL_FOLDER_ID", None),
            patch.object(write_tools, "resolve_folder_id", return_value=UUID_F),
            patch.object(write_tools, "make_post_request", side_effect=post),
            patch.object(
                write_tools,
                "make_delete_request",
                return_value=delete or _response(204),
            ),
        )

    def test_creates_the_evidence_and_returns_the_curl(self):
        post = self._post(
            _response(201, {"id": UUID_A, "name": "Audit"}), _response(200, ISSUED)
        )
        p1, p2, p3, p4 = self._patches(post)
        with p1, p2, p3, p4:
            out = run(
                write_tools.prepare_evidence_upload(
                    filename="audit.pdf", name="Audit", folder_id="Acme"
                )
            )
        assert post.sent == [
            ("/evidences/", {"name": "Audit", "folder": UUID_F}),
            (f"/evidences/{UUID_A}/upload-url/", {"filename": "audit.pdf"}),
        ]
        assert f"(ID: {UUID_A})" in out
        assert ISSUED["expires_at"] in out
        assert (
            "curl -sS --fail-with-body -X POST "
            "-H 'Content-Type: application/octet-stream' "
            f"--data-binary @\"<sandbox path>\" '{UPLOAD_URL}'"
        ) in out
        # A path with spaces stays one argument once substituted.
        command = next(line for line in out.splitlines() if line.startswith("curl"))
        args = shlex.split(
            command.replace("<sandbox path>", "/mnt/data/audit report.pdf")
        )
        assert "@/mnt/data/audit report.pdf" in args

    def test_never_puts_a_credential_in_the_curl(self):
        post = self._post(
            _response(201, {"id": UUID_A, "name": "a"}), _response(200, ISSUED)
        )
        p1, p2, p3, p4 = self._patches(post)
        with p1, p2, p3, p4:
            out = run(write_tools.prepare_evidence_upload(filename="a.pdf"))
        assert "Authorization" not in out
        assert "Token " not in out and "Bearer" not in out

    def test_existing_evidence_is_not_recreated(self):
        post = self._post(_response(200, ISSUED))
        p1, p2, p3, p4 = self._patches(post)
        with (
            p1,
            p2,
            p3,
            p4,
            patch("ca_mcp.resolvers.resolve_evidence_id", return_value=UUID_B),
        ):
            out = run(
                write_tools.prepare_evidence_upload(
                    filename="new.pdf", evidence_id="Existing"
                )
            )
        assert post.sent == [
            (f"/evidences/{UUID_B}/upload-url/", {"filename": "new.pdf"})
        ]
        assert f"Evidence ID: {UUID_B}" in out
        assert UPLOAD_URL in out

    def test_existing_evidence_without_change_permission(self):
        post = self._post(_response(403, text="denied"))
        p1, p2, p3, p4 = self._patches(post)
        with (
            p1,
            p2,
            p3,
            p4 as delete,
            patch("ca_mcp.resolvers.resolve_evidence_id", return_value=UUID_B),
        ):
            out = run(
                write_tools.prepare_evidence_upload(
                    filename="a.pdf", evidence_id=UUID_B
                )
            )
        assert out == "Error getting an upload URL: 403 - denied"
        delete.assert_not_called()

    def test_new_evidence_is_rolled_back_when_no_url_is_issued(self):
        post = self._post(
            _response(201, {"id": UUID_A, "name": "a"}), _response(500, text="boom")
        )
        p1, p2, p3, p4 = self._patches(post)
        with p1, p2, p3, p4 as delete:
            out = run(write_tools.prepare_evidence_upload(filename="a.pdf"))
        assert out.startswith("Error getting an upload URL: 500 - boom")
        delete.assert_called_once_with(f"/evidences/{UUID_A}/")

    def test_new_evidence_is_rolled_back_on_an_unexpected_error(self):
        post = self._post(
            _response(201, {"id": UUID_A, "name": "a"}), _response(200, {})
        )
        p1, p2, p3, p4 = self._patches(post)
        with p1, p2, p3, p4 as delete:
            out = run(write_tools.prepare_evidence_upload(filename="a.pdf"))
        assert out.startswith("Error in prepare_evidence_upload:")
        delete.assert_called_once_with(f"/evidences/{UUID_A}/")

    def test_retry_hint_names_the_evidence(self):
        post = self._post(
            _response(201, {"id": UUID_A, "name": "a"}), _response(200, ISSUED)
        )
        p1, p2, p3, p4 = self._patches(post)
        with p1, p2, p3, p4:
            out = run(write_tools.prepare_evidence_upload(filename="a.pdf"))
        assert f"evidence_id={UUID_A}" in out

    def test_creation_failure_is_reported(self):
        post = self._post(_response(400, text="bad status"))
        p1, p2, p3, p4 = self._patches(post)
        with p1, p2, p3, p4:
            out = run(
                write_tools.prepare_evidence_upload(filename="a.pdf", status="nope")
            )
        assert out == "Error creating evidence: 400 - bad status"
        assert len(post.sent) == 1

    def test_filename_is_required_and_reduced_to_its_base_name(self):
        post = self._post(
            _response(201, {"id": UUID_A, "name": "x"}), _response(200, ISSUED)
        )
        p1, p2, p3, p4 = self._patches(post)
        with p1, p2, p3, p4:
            assert "filename is required" in run(
                write_tools.prepare_evidence_upload(filename="  ")
            )
            run(write_tools.prepare_evidence_upload(filename="/mnt/data/x.pdf"))
        assert post.sent[0][1]["name"] == "x.pdf"
        assert post.sent[1][1] == {"filename": "x.pdf"}


def test_prepare_evidence_upload_needs_create_and_update():
    assert write_tools.prepare_evidence_upload in server.WRITE_TOOLS
    assert server.needed_actions("prepare_evidence_upload") == {
        server.actions.CREATE,
        server.actions.UPDATE,
    }


def test_prepare_evidence_upload_is_only_registered_remotely():
    from mcp.server.mcpserver import MCPServer

    def names(is_http):
        fresh = MCPServer("test")
        with (
            patch.object(server, "mcp", fresh),
            patch.object(server, "_registered", False),
            patch.object(server.config, "IS_HTTP", is_http),
        ):
            server.register_tools(read_only=False)
            return {t.name for t in asyncio.run(fresh.list_tools())}

    assert "prepare_evidence_upload" not in names(False)
    assert "prepare_evidence_upload" in names(True)


def test_the_oauth_server_offers_prepare_evidence_upload(monkeypatch):
    monkeypatch.setattr(server.config, "IS_HTTP", False)
    app = server.ActionFilteredServer("test")
    server._register_on(app, read_only=False, remote=True)
    names = {tool.name for tool in app._tool_manager.list_tools()}
    assert "prepare_evidence_upload" in names
    assert "create_evidence" not in names
