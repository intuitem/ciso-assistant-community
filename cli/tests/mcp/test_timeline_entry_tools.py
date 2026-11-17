"""Unit tests for the MCP timeline entry tools.

create_timeline_entry / update_timeline_entry; network calls and resolvers are
mocked at their import sites.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest


sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import resolvers  # noqa: E402
from ca_mcp.tools import (  # noqa: E402
    update_tools,
    write_tools,
)
from tests.mcp.helpers import (  # noqa: E402
    UUID_A,
    UUID_B,
    UUID_C,
    UUID_D,
    UUID_F,
    _response,
    _router,
    run,
)

TYPE_ERROR = "Error: entry_type must be one of detection, mitigation, observation"


FUTURE_BODY = '{"non_field_errors": ["Timestamp cannot be in the future."]}'


class TestCreateTimelineEntry:
    @pytest.fixture(autouse=True)
    def incident_get(self):
        with patch.object(
            write_tools,
            "make_get_request",
            return_value=_response(200, {"id": UUID_A, "folder": {"id": UUID_F}}),
        ) as get:
            yield get

    def _patch_ok(self):
        return patch.object(
            write_tools,
            "make_post_request",
            return_value=_response(201, {"id": UUID_B, "entry": "Mail blocked"}),
        )

    def test_minimal_resolves_incident_by_name(self, incident_get):
        fake = _router({"/incidents/": [{"id": UUID_A, "name": "Phishing"}]})
        with (
            self._patch_ok() as post,
            patch.object(resolvers, "fetch_all_results", side_effect=fake),
        ):
            result = run(
                write_tools.create_timeline_entry(
                    incident_id="Phishing", entry="Mail blocked"
                )
            )
        assert result == f"Created timeline entry: Mail blocked (ID: {UUID_B})"
        incident_get.assert_called_once_with(f"/incidents/{UUID_A}/")
        assert post.call_args.args == (
            "/timeline-entries/",
            {"incident": UUID_A, "entry": "Mail blocked", "folder": UUID_F},
        )

    def test_folder_as_plain_id(self, incident_get):
        incident_get.return_value = _response(200, {"id": UUID_A, "folder": UUID_D})
        with self._patch_ok() as post:
            run(write_tools.create_timeline_entry(incident_id=UUID_A, entry="x"))
        assert post.call_args.args[1]["folder"] == UUID_D

    def test_incident_get_failure_reported(self, incident_get):
        incident_get.return_value = _response(403, text="Forbidden")
        with self._patch_ok() as post:
            result = run(
                write_tools.create_timeline_entry(incident_id=UUID_A, entry="x")
            )
        assert result == "Error creating timeline entry: 403 - Forbidden"
        post.assert_not_called()

    def test_full_payload(self):
        with self._patch_ok() as post:
            run(
                write_tools.create_timeline_entry(
                    incident_id=UUID_A,
                    entry="Mail blocked",
                    entry_type="mitigation",
                    timestamp="2026-01-01T10:00:00Z",
                    observation="Sender domain blocklisted",
                    evidences=[UUID_C],
                )
            )
        assert post.call_args.args == (
            "/timeline-entries/",
            {
                "incident": UUID_A,
                "entry": "Mail blocked",
                "folder": UUID_F,
                "entry_type": "mitigation",
                "timestamp": "2026-01-01T10:00:00Z",
                "observation": "Sender domain blocklisted",
                "evidences": [UUID_C],
            },
        )

    def test_automatic_type_rejected_without_request(self, incident_get):
        with (
            self._patch_ok() as post,
            patch.object(write_tools, "resolve_incident_id") as r_incident,
        ):
            result = run(
                write_tools.create_timeline_entry(
                    incident_id="Phishing", entry="x", entry_type="status_changed"
                )
            )
        assert result == TYPE_ERROR
        r_incident.assert_not_called()
        incident_get.assert_not_called()
        post.assert_not_called()

    def test_unknown_incident_reported(self):
        fake = _router({"/incidents/": []})
        with (
            self._patch_ok() as post,
            patch.object(resolvers, "fetch_all_results", side_effect=fake),
        ):
            result = run(
                write_tools.create_timeline_entry(incident_id="Nope", entry="x")
            )
        assert result == "Error in create_timeline_entry: Incident 'Nope' not found"
        post.assert_not_called()

    def test_backend_rejection_returned(self):
        with patch.object(
            write_tools,
            "make_post_request",
            return_value=_response(400, text=FUTURE_BODY),
        ):
            result = run(
                write_tools.create_timeline_entry(
                    incident_id=UUID_A, entry="x", timestamp="2999-01-01T00:00:00Z"
                )
            )
        assert result == f"Error creating timeline entry: 400 - {FUTURE_BODY}"

    def test_exception_reported(self):
        with patch.object(
            write_tools, "make_post_request", side_effect=RuntimeError("boom")
        ):
            result = run(
                write_tools.create_timeline_entry(incident_id=UUID_A, entry="x")
            )
        assert result == "Error in create_timeline_entry: boom"


class TestUpdateTimelineEntry:
    def _patch_get(self, entry_type="observation", status=200, text=""):
        return patch.object(
            update_tools,
            "make_get_request",
            return_value=_response(
                status, {"id": UUID_B, "entry_type": entry_type}, text=text
            ),
        )

    def _patch_ok(self):
        return patch.object(
            update_tools,
            "make_patch_request",
            return_value=_response(200, {"id": UUID_B, "entry": "Mail blocked"}),
        )

    def test_partial_update(self):
        with self._patch_get() as get, self._patch_ok() as patch_req:
            result = run(
                update_tools.update_timeline_entry(
                    timeline_entry_id=UUID_B, observation="More details"
                )
            )
        assert result == f"Updated timeline entry: Mail blocked (ID: {UUID_B})"
        get.assert_called_once_with(f"/timeline-entries/{UUID_B}/")
        assert patch_req.call_args.args == (
            f"/timeline-entries/{UUID_B}/",
            {"observation": "More details"},
        )

    def test_full_payload_and_empty_evidences(self):
        with self._patch_get("detection"), self._patch_ok() as patch_req:
            run(
                update_tools.update_timeline_entry(
                    timeline_entry_id=UUID_B,
                    entry="Fixed text",
                    entry_type="mitigation",
                    timestamp="2026-01-01T10:00:00Z",
                    evidences=[],
                )
            )
        assert patch_req.call_args.args[1] == {
            "entry": "Fixed text",
            "entry_type": "mitigation",
            "timestamp": "2026-01-01T10:00:00Z",
            "evidences": [],
        }

    def test_automatic_type_input_rejected_without_request(self):
        with self._patch_get() as get, self._patch_ok() as patch_req:
            result = run(
                update_tools.update_timeline_entry(
                    timeline_entry_id=UUID_B, entry_type="severity_changed"
                )
            )
        assert result == TYPE_ERROR
        get.assert_not_called()
        patch_req.assert_not_called()

    @pytest.mark.parametrize(
        "current_type", ["status_changed", "severity_changed", None, "bogus"]
    )
    def test_non_manual_entry_not_modified(self, current_type):
        with self._patch_get(current_type) as get, self._patch_ok() as patch_req:
            result = run(
                update_tools.update_timeline_entry(
                    timeline_entry_id=UUID_B, observation="x"
                )
            )
        assert result == (
            f"Error: cannot modify automatic timeline entry ({current_type})"
        )
        get.assert_called_once()
        patch_req.assert_not_called()

    @pytest.mark.parametrize("bad_id", ["../incidents/" + UUID_A, "Mail blocked"])
    def test_non_uuid_id_rejected_without_request(self, bad_id):
        with self._patch_get() as get, self._patch_ok() as patch_req:
            result = run(
                update_tools.update_timeline_entry(
                    timeline_entry_id=bad_id, observation="x"
                )
            )
        assert result == "Error: timeline_entry_id must be a UUID"
        get.assert_not_called()
        patch_req.assert_not_called()

    def test_empty_update_sends_nothing(self):
        with self._patch_get() as get, self._patch_ok() as patch_req:
            result = run(update_tools.update_timeline_entry(timeline_entry_id=UUID_B))
        assert result == "Error: No fields provided to update"
        get.assert_not_called()
        patch_req.assert_not_called()

    def test_unknown_entry_get_failure_reported(self):
        with (
            self._patch_get(status=404, text="Not found.") as get,
            self._patch_ok() as patch_req,
        ):
            result = run(
                update_tools.update_timeline_entry(
                    timeline_entry_id=UUID_C, observation="x"
                )
            )
        assert result == "Error updating timeline entry: 404 - Not found."
        get.assert_called_once()
        patch_req.assert_not_called()

    def test_backend_rejection_returned(self):
        with (
            self._patch_get(),
            patch.object(
                update_tools,
                "make_patch_request",
                return_value=_response(400, text='{"entry": ["too long"]}'),
            ),
        ):
            result = run(
                update_tools.update_timeline_entry(
                    timeline_entry_id=UUID_B, entry="x" * 201
                )
            )
        assert result == 'Error updating timeline entry: 400 - {"entry": ["too long"]}'

    def test_exception_reported(self):
        with patch.object(
            update_tools, "make_get_request", side_effect=RuntimeError("boom")
        ):
            result = run(
                update_tools.update_timeline_entry(
                    timeline_entry_id=UUID_B, observation="x"
                )
            )
        assert result == "Error in update_timeline_entry: boom"


class TestRegistration:
    def test_timeline_entry_tools_are_write_tools(self):
        from ca_mcp import server

        names = {"create_timeline_entry", "update_timeline_entry"}
        write_names = {t.__name__ for t in server.WRITE_TOOLS}
        read_names = {t.__name__ for t in server.READ_TOOLS}
        assert names <= write_names
        assert not names & read_names
        assert "delete_timeline_entry" not in write_names | read_names
