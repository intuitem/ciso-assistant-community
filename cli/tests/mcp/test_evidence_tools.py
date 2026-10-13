"""Unit tests for the MCP create_evidence tool and the raw-body upload helper.

Network calls are mocked at their import sites, as in
test_risk_review_tools.py; files are real, under pytest's tmp_path.
"""

import sys
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import client  # noqa: E402
from ca_mcp import server  # noqa: E402
from ca_mcp.tools import write_tools  # noqa: E402
from tests.mcp.helpers import (  # noqa: E402
    UUID_A,
    UUID_F,
    _response,
    run,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24


class _Mocks:
    """Patch every network entry point of create_evidence at once."""

    def __init__(self, create=None, upload=None, is_http=False):
        self.create = create or _response(201, {"id": UUID_A, "name": "Alert"})
        self.upload = upload or _response(200)
        self.is_http = is_http

    def __enter__(self):
        self._patches = [
            patch.object(write_tools.config, "IS_HTTP", self.is_http),
            patch.object(write_tools, "GLOBAL_FOLDER_ID", None),
            patch.object(write_tools, "resolve_folder_id", return_value=UUID_F),
            patch.object(write_tools, "make_post_request", return_value=self.create),
            patch.object(write_tools, "make_upload_request", return_value=self.upload),
            patch.object(
                write_tools, "make_delete_request", return_value=_response(204)
            ),
        ]
        mocks = [p.__enter__() for p in self._patches]
        self.resolve, self.post, self.up, self.delete = mocks[2:]
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
        assert m.up.call_args.args == (
            f"/evidences/{UUID_A}/upload/",
            "alert.pdf",
            path.read_bytes(),
        )
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
        assert m.up.call_args.args[1:] == ("a.png", PNG_BYTES)

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

    def test_directory_is_not_a_file(self, tmp_path):
        folder = tmp_path / "shots.png"
        folder.mkdir()
        with _Mocks() as m:
            out = run(write_tools.create_evidence(file_path=str(folder)))
        assert out == f"Error: file not found: {folder}"
        m.assert_no_request()

    def test_extension_is_case_insensitive(self, tmp_path):
        path = _file(tmp_path, "ALERT.JPG")
        with _Mocks() as m:
            out = run(write_tools.create_evidence(file_path=str(path)))
        assert out.startswith("Created evidence:")
        m.up.assert_called_once()

    def test_unsupported_types(self, tmp_path):
        for name, ext in (("tool.exe", ".exe"), ("README", "")):
            path = _file(tmp_path, name)
            with _Mocks() as m:
                out = run(write_tools.create_evidence(file_path=str(path)))
            assert out.startswith(f"Error: unsupported file type '{ext}' (allowed: ")
            m.assert_no_request()

    def test_backend_types_are_accepted(self, tmp_path):
        for name in ("logo.svg", "report.docx", "export.csv", "mail.eml", "logs.zip"):
            path = _file(tmp_path, name)
            with _Mocks() as m:
                out = run(write_tools.create_evidence(file_path=str(path)))
            assert out.startswith("Created evidence:"), name
            m.up.assert_called_once()

    def test_matches_backend_allowlist(self):
        validators = Path(__file__).parents[3] / "backend/core/validators.py"
        source = validators.read_text(encoding="utf-8")
        block = source.split("ALLOWED_UPLOAD_EXTENSIONS = [", 1)[1].split("]", 1)[0]
        backend = {f".{e.strip().strip('"')}" for e in block.split(",") if e.strip()}
        assert set(write_tools.EVIDENCE_ALLOWED_EXTENSIONS) == backend

    def test_too_large_is_refused_before_reading(self, tmp_path):
        path = _file(tmp_path, "big.pdf", b"x" * 2_000_001)
        with (
            _Mocks() as m,
            patch.object(write_tools.config, "MAX_UPLOAD_MB", 2),
            patch.object(Path, "read_bytes") as read,
        ):
            out = run(write_tools.create_evidence(file_path=str(path)))
        assert out == "Error: file too large: 2.0 MB (max 2 MB)"
        read.assert_not_called()
        m.assert_no_request()

    def test_refused_over_http(self, tmp_path):
        path = _file(tmp_path, "alert.png")
        with (
            _Mocks(is_http=True) as m,
            patch.object(Path, "read_bytes") as read_bytes,
        ):
            out = run(write_tools.create_evidence(file_path=str(path)))
        assert out == (
            "Error: create_evidence is only available with the local stdio transport"
        )
        read_bytes.assert_not_called()
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

    def test_upload_exception_deletes_evidence(self, tmp_path):
        path = _file(tmp_path, "alert.png")
        with _Mocks() as m:
            m.up.side_effect = TimeoutError("read timed out")
            out = run(write_tools.create_evidence(file_path=str(path)))
        assert out == "Error in create_evidence: read timed out"
        m.delete.assert_called_once_with(f"/evidences/{UUID_A}/")

    def test_empty_file_is_refused(self, tmp_path):
        path = _file(tmp_path, "blank.png", b"")
        with _Mocks() as m:
            out = run(write_tools.create_evidence(file_path=str(path)))
        assert out == f"Error: file is empty: {path}"
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

    def test_raising_rollback_keeps_the_upload_error(self, tmp_path):
        path = _file(tmp_path, "alert.png")
        with _Mocks() as m:
            m.up.side_effect = TimeoutError("read timed out")
            m.delete.side_effect = ConnectionError("connection reset")
            out = run(write_tools.create_evidence(file_path=str(path)))
        assert out == (
            "Error in create_evidence: read timed out"
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
