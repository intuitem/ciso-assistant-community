"""Unit tests for linking evidences to audit requirements: the ref-ID resolver,
create_evidence(requirement_assessments=...) and update_evidence(add_/remove_...).

Network calls are mocked at their import sites; files are real, under tmp_path.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import resolvers  # noqa: E402
from ca_mcp.tools import update_tools, write_tools  # noqa: E402
from tests.mcp.helpers import (  # noqa: E402
    UUID_A,
    UUID_B,
    UUID_C,
    UUID_D,
    UUID_F,
    _response,
    run,
)

AUDIT = "IDM Platform C5:2026 Type 1"
RAS = [
    {"id": UUID_B, "requirement": {"ref_id": "AM-02.04B"}},
    {"id": UUID_C, "requirement": {"ref_id": "AM-02.05B"}},
]


def _lookup(ras=RAS, error=None):
    return (
        patch.object(
            resolvers, "resolve_compliance_assessment_id", return_value=UUID_D
        ),
        patch.object(resolvers, "fetch_all_results", return_value=(ras, error)),
    )


class TestResolveRequirementAssessmentIds:
    def test_uuid_passthrough_without_audit(self):
        with patch.object(resolvers, "fetch_all_results") as fetch:
            assert resolvers.resolve_requirement_assessment_ids([UUID_B]) == [UUID_B]
        fetch.assert_not_called()

    def test_ref_ids_case_insensitive_and_deduplicated(self):
        resolve_ca, fetch = _lookup()
        with resolve_ca as ca, fetch as f:
            out = resolvers.resolve_requirement_assessment_ids(
                ["am-02.04b", " AM-02.05B ", "AM-02.04B", UUID_A], AUDIT
            )
        assert out == [UUID_B, UUID_C, UUID_A]
        ca.assert_called_once_with(AUDIT)
        assert f.call_args.kwargs["params"] == {"compliance_assessment": UUID_D}
        assert f.call_args.kwargs["max_items"] is None

    def test_unknown_refs_are_all_named(self):
        resolve_ca, fetch = _lookup()
        with resolve_ca, fetch, pytest.raises(ValueError, match="AM-99.01B, AM-98.01B"):
            resolvers.resolve_requirement_assessment_ids(
                ["AM-99.01B", "AM-02.04B", "AM-98.01B"], AUDIT
            )

    def test_ref_id_needs_audit(self):
        with pytest.raises(ValueError, match="pass compliance_assessment"):
            resolvers.resolve_requirement_assessment_ids(["AM-02.04B"])

    def test_api_error(self):
        resolve_ca, fetch = _lookup(ras=[], error="503")
        with resolve_ca, fetch, pytest.raises(ValueError, match="API error: 503"):
            resolvers.resolve_requirement_assessment_ids(["AM-02.04B"], AUDIT)

    def test_empty(self):
        assert resolvers.resolve_requirement_assessment_ids(None) == []


def _create_mocks():
    return [
        patch.object(write_tools, "GLOBAL_FOLDER_ID", None),
        patch.object(write_tools, "resolve_folder_id", return_value=UUID_F),
        patch.object(
            write_tools,
            "make_post_request",
            return_value=_response(201, {"id": UUID_A, "name": "Log"}),
        ),
        patch.object(write_tools, "make_upload_request", return_value=_response(200)),
        patch.object(
            write_tools,
            "make_get_request",
            return_value=_response(200, {"attachment": "/media/log.md"}),
        ),
    ]


class TestCreateEvidenceWithRequirements:
    def test_links_in_payload(self, tmp_path):
        path = tmp_path / "log.md"
        path.write_text("# log", encoding="utf-8")
        patches = _create_mocks()
        resolve_ca, fetch = _lookup()
        with resolve_ca, fetch:
            started = [p.__enter__() for p in patches]
            try:
                out = run(
                    write_tools.create_evidence(
                        file_path=str(path),
                        name="Log",
                        folder_id="IDM Platform",
                        requirement_assessments=["AM-02.04B"],
                        compliance_assessment=AUDIT,
                    )
                )
            finally:
                for p in reversed(patches):
                    p.__exit__(None, None, None)
        post = started[2]
        assert post.call_args.args[1]["requirement_assessments"] == [UUID_B]
        assert out.startswith(f"Created evidence: Log (ID: {UUID_A})")

    def test_unknown_requirement_creates_nothing(self, tmp_path):
        path = tmp_path / "log.md"
        path.write_text("# log", encoding="utf-8")
        patches = _create_mocks()
        resolve_ca, fetch = _lookup()
        with resolve_ca, fetch:
            started = [p.__enter__() for p in patches]
            try:
                out = run(
                    write_tools.create_evidence(
                        file_path=str(path),
                        requirement_assessments=["AM-99.01B"],
                        compliance_assessment=AUDIT,
                    )
                )
            finally:
                for p in reversed(patches):
                    p.__exit__(None, None, None)
        started[2].assert_not_called()
        started[3].assert_not_called()
        assert "AM-99.01B" in out and out.startswith("Error")

    def test_without_requirements_payload_unchanged(self, tmp_path):
        path = tmp_path / "log.md"
        path.write_text("# log", encoding="utf-8")
        patches = _create_mocks()
        started = [p.__enter__() for p in patches]
        try:
            run(write_tools.create_evidence(file_path=str(path), name="Log"))
        finally:
            for p in reversed(patches):
                p.__exit__(None, None, None)
        assert "requirement_assessments" not in started[2].call_args.args[1]


class TestUpdateEvidenceRequirements:
    def _run(self, current, **kwargs):
        resolve_ca, fetch = _lookup()
        with (
            resolve_ca,
            fetch,
            patch.object(update_tools, "resolve_evidence_id", return_value=UUID_A),
            patch.object(
                update_tools,
                "make_get_request",
                return_value=_response(200, {"requirement_assessments": current}),
            ),
            patch.object(
                update_tools,
                "make_patch_request",
                return_value=_response(200, {"id": UUID_A, "name": "Log"}),
            ) as patch_req,
        ):
            out = run(
                update_tools.update_evidence(
                    UUID_A, compliance_assessment=AUDIT, **kwargs
                )
            )
        return out, patch_req

    def test_add_keeps_existing_links(self):
        out, patch_req = self._run(
            [{"id": UUID_D, "str": "OIS-01.01B"}],
            add_requirement_assessments=["AM-02.04B", "AM-02.05B"],
        )
        assert patch_req.call_args.args == (
            f"/evidences/{UUID_A}/",
            {"requirement_assessments": [UUID_D, UUID_B, UUID_C]},
        )
        assert out == f"Updated evidence: Log (ID: {UUID_A})"

    def test_add_existing_is_idempotent(self):
        _, patch_req = self._run([UUID_B], add_requirement_assessments=["AM-02.04B"])
        assert patch_req.call_args.args[1] == {"requirement_assessments": [UUID_B]}

    def test_remove(self):
        _, patch_req = self._run(
            [UUID_B, UUID_C], remove_requirement_assessments=["AM-02.04B"]
        )
        assert patch_req.call_args.args[1] == {"requirement_assessments": [UUID_C]}

    def test_unknown_ref_writes_nothing(self):
        out, patch_req = self._run([], add_requirement_assessments=["AM-99.01B"])
        patch_req.assert_not_called()
        assert out.startswith("Error") and "AM-99.01B" in out
