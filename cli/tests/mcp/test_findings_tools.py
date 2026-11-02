"""Unit tests for the MCP findings tools: findings assessments (binders) in the
generic registry, create_findings_assessment, create_finding, update_finding,
the binder/status options of create_evidence and their registration.

Network calls and resolvers are mocked at their import sites.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import resolvers  # noqa: E402
from ca_mcp import server  # noqa: E402
from ca_mcp.tools import generic_tools, update_tools, write_tools  # noqa: E402
from tests.mcp.helpers import (  # noqa: E402
    UUID_A,
    UUID_B,
    UUID_C,
    UUID_F,
    _response,
    _router,
    run,
)

GLOBAL = "99999999-9999-9999-9999-999999999999"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
NEW_TOOLS = {"create_findings_assessment", "create_finding", "update_finding"}


# ---------------------------------------------------------------------------
# generic registry
# ---------------------------------------------------------------------------


def test_findings_assessments_registered():
    assert generic_tools.OBJECTS["findings_assessments"] == "findings-assessments"


def test_list_findings_assessments():
    get = _response(
        200, {"count": 1, "results": [{"id": UUID_A, "name": "Pentest Q4"}]}
    )
    with patch.object(generic_tools, "make_get_request", return_value=get) as req:
        result = run(generic_tools.list_objects("findings_assessments"))
    assert req.call_args.args[0] == "/findings-assessments/"
    assert "Pentest Q4" in str(result)


# ---------------------------------------------------------------------------
# resolvers
# ---------------------------------------------------------------------------


class TestResolvers:
    def test_uuid_passes_through(self):
        with patch.object(resolvers, "fetch_all_results") as fetch:
            assert resolvers.resolve_findings_assessment_id(UUID_A) == UUID_A
            assert resolvers.resolve_finding_id(UUID_B) == UUID_B
        fetch.assert_not_called()

    def test_binder_name_uses_exact_filter_without_cap(self):
        fake = _router({"/findings-assessments/": [{"id": UUID_A, "name": "Q4"}]})
        with patch.object(resolvers, "fetch_all_results", side_effect=fake) as fetch:
            assert resolvers.resolve_findings_assessment_id("Q4") == UUID_A
        assert fake.calls == [("/findings-assessments/", {"name": "Q4"})]
        assert fetch.call_args.kwargs["max_items"] is None

    def test_finding_name_ambiguous_refused(self):
        rows = [{"id": UUID_A, "name": "XSS"}, {"id": UUID_B, "name": "XSS"}]
        fake = _router({"/findings/": rows})
        with (
            patch.object(resolvers, "fetch_all_results", side_effect=fake),
            pytest.raises(ValueError, match="Ambiguous finding name 'XSS'"),
        ):
            resolvers.resolve_finding_id("XSS")

    def test_not_found(self):
        fake = _router({})
        with (
            patch.object(resolvers, "fetch_all_results", side_effect=fake),
            pytest.raises(ValueError, match="Findings assessment 'Nope'"),
        ):
            resolvers.resolve_findings_assessment_id("Nope")

    @pytest.mark.parametrize("ref", ["", "   "])
    def test_empty_reference_refused(self, ref):
        with (
            patch.object(resolvers, "fetch_all_results") as fetch,
            pytest.raises(ValueError, match="reference is empty"),
        ):
            resolvers.resolve_finding_id(ref)
        fetch.assert_not_called()

    def test_api_error(self):
        with (
            patch.object(resolvers, "fetch_all_results", return_value=([], "boom")),
            pytest.raises(ValueError, match="API error: boom"),
        ):
            resolvers.resolve_finding_id("XSS")


# ---------------------------------------------------------------------------
# create_findings_assessment
# ---------------------------------------------------------------------------


class TestCreateFindingsAssessment:
    def test_creates_binder(self):
        with (
            patch.object(
                write_tools,
                "make_post_request",
                return_value=_response(201, {"id": UUID_A, "name": "Pentest Q4"}),
            ) as post,
            patch.object(write_tools, "GLOBAL_FOLDER_ID", GLOBAL),
            patch.object(write_tools, "resolve_folder_id", return_value=UUID_F),
        ):
            result = run(
                write_tools.create_findings_assessment(
                    name="Pentest Q4",
                    folder_id="Security",
                    category="self_identified",
                    status="in_review",
                    start_date="2026-10-01",
                    reported_at="2026-10-15",
                    description="External pentest",
                    ref_id="PT-Q4",
                )
            )

        assert result == f"Created findings assessment: Pentest Q4 (ID: {UUID_A})"
        assert post.call_args.args == (
            "/findings-assessments/",
            {
                "name": "Pentest Q4",
                "folder": UUID_F,
                "category": "self_identified",
                "status": "in_review",
                "start_date": "2026-10-01",
                "reported_at": "2026-10-15",
                "description": "External pentest",
                "ref_id": "PT-Q4",
            },
        )

    def test_defaults_to_global_folder(self):
        with (
            patch.object(
                write_tools,
                "make_post_request",
                return_value=_response(201, {"id": UUID_A, "name": "Q4"}),
            ) as post,
            patch.object(write_tools, "GLOBAL_FOLDER_ID", GLOBAL),
            patch.object(
                write_tools, "resolve_folder_id", side_effect=lambda f: f
            ) as resolve,
        ):
            run(write_tools.create_findings_assessment(name="Q4"))
        resolve.assert_called_once_with(GLOBAL)
        assert post.call_args.args[1] == {"name": "Q4", "folder": GLOBAL}

    def test_duplicate_returns_backend_body_without_retry(self):
        body = '{"name": ["Name already exists"]}'
        with (
            patch.object(
                write_tools,
                "make_post_request",
                return_value=_response(400, text=body),
            ) as post,
            patch.object(write_tools, "GLOBAL_FOLDER_ID", GLOBAL),
            patch.object(write_tools, "resolve_folder_id", return_value=UUID_F),
        ):
            result = run(write_tools.create_findings_assessment(name="Q4"))
        assert result == f"Error creating findings assessment: 400 - {body}"
        assert post.call_count == 1


# ---------------------------------------------------------------------------
# create_finding
# ---------------------------------------------------------------------------


class TestCreateFinding:
    def test_creates_finding_with_label_severity(self):
        with (
            patch.object(
                write_tools,
                "make_post_request",
                return_value=_response(
                    201, {"id": UUID_C, "name": "SQLi", "severity": 3}
                ),
            ) as post,
            patch.object(
                resolvers, "resolve_findings_assessment_id", return_value=UUID_A
            ) as binder,
            patch.object(
                resolvers, "resolve_evidence_id", side_effect=lambda v: f"ev-{v}"
            ),
        ):
            result = run(
                write_tools.create_finding(
                    name="SQLi",
                    findings_assessment_id="Pentest Q4",
                    severity="High",
                    status="identified",
                    eta="2026-12-01",
                    evidences=["Report"],
                    description="Login form injectable",
                    ref_id="F-01",
                )
            )

        assert result == f"Created finding: SQLi (ID: {UUID_C}, severity: high)"
        binder.assert_called_once_with("Pentest Q4")
        assert post.call_args.args == (
            "/findings/",
            {
                "name": "SQLi",
                "findings_assessment": UUID_A,
                "severity": 3,
                "description": "Login form injectable",
                "status": "identified",
                "eta": "2026-12-01",
                "evidences": ["ev-Report"],
                "ref_id": "F-01",
            },
        )

    @pytest.mark.parametrize(
        "label,value",
        [
            ("undefined", -1),
            ("info", 0),
            ("low", 1),
            ("medium", 2),
            ("high", 3),
            ("CRITICAL", 4),
        ],
    )
    def test_severity_labels(self, label, value):
        assert write_tools._severity_value(label) == value
        assert write_tools._severity_label(value) == label.lower()

    def test_bad_severity_sends_no_request(self):
        with (
            patch.object(write_tools, "make_post_request") as post,
            patch.object(resolvers, "resolve_findings_assessment_id") as binder,
        ):
            result = run(
                write_tools.create_finding(
                    name="SQLi", findings_assessment_id="Q4", severity="severe"
                )
            )
        assert result == (
            "Error: invalid severity 'severe' "
            "(allowed: undefined, info, low, medium, high, critical)"
        )
        post.assert_not_called()
        binder.assert_not_called()

    def test_locked_binder_returns_backend_body(self):
        body = '{"findings_assessment": "Cannot attach the finding to a locked findings assessment."}'
        with (
            patch.object(
                write_tools,
                "make_post_request",
                return_value=_response(400, text=body),
            ),
            patch.object(
                resolvers, "resolve_findings_assessment_id", return_value=UUID_A
            ),
        ):
            result = run(
                write_tools.create_finding(name="SQLi", findings_assessment_id=UUID_A)
            )
        assert result == f"Error creating finding: 400 - {body}"

    def test_unknown_binder(self):
        with (
            patch.object(write_tools, "make_post_request") as post,
            patch.object(
                resolvers,
                "resolve_findings_assessment_id",
                side_effect=ValueError("Findings assessment 'Q9' not found"),
            ),
        ):
            result = run(
                write_tools.create_finding(name="SQLi", findings_assessment_id="Q9")
            )
        assert result == ("Error in create_finding: Findings assessment 'Q9' not found")
        post.assert_not_called()


# ---------------------------------------------------------------------------
# update_finding
# ---------------------------------------------------------------------------


class TestUpdateFinding:
    def test_patches_given_fields_only(self):
        with (
            patch.object(
                update_tools,
                "make_patch_request",
                return_value=_response(
                    200, {"id": UUID_C, "name": "SQLi", "severity": 4}
                ),
            ) as patch_request,
            patch.object(resolvers, "resolve_finding_id", return_value=UUID_C),
        ):
            result = run(
                update_tools.update_finding(
                    finding_id="SQLi", severity="critical", status="confirmed"
                )
            )
        assert result == f"Updated finding: SQLi (ID: {UUID_C}, severity: critical)"
        assert patch_request.call_args.args == (
            f"/findings/{UUID_C}/",
            {"severity": 4, "status": "confirmed"},
        )

    def test_patches_every_field(self):
        with (
            patch.object(
                update_tools,
                "make_patch_request",
                return_value=_response(
                    200, {"id": UUID_C, "name": "SQLi v2", "severity": 2}
                ),
            ) as patch_request,
            patch.object(resolvers, "resolve_finding_id", return_value=UUID_C),
            patch.object(
                resolvers, "resolve_evidence_id", side_effect=lambda v: f"ev-{v}"
            ),
        ):
            result = run(
                update_tools.update_finding(
                    finding_id=UUID_C,
                    name="SQLi v2",
                    severity="medium",
                    description="Retested",
                    status="mitigated",
                    eta="2027-01-15",
                    evidences=["Retest report"],
                    ref_id="F-01",
                )
            )
        assert result == f"Updated finding: SQLi v2 (ID: {UUID_C}, severity: medium)"
        assert patch_request.call_args.args == (
            f"/findings/{UUID_C}/",
            {
                "name": "SQLi v2",
                "severity": 2,
                "description": "Retested",
                "status": "mitigated",
                "eta": "2027-01-15",
                "evidences": ["ev-Retest report"],
                "ref_id": "F-01",
            },
        )

    def test_nothing_given(self):
        with (
            patch.object(update_tools, "make_patch_request") as patch_request,
            patch.object(resolvers, "resolve_finding_id") as resolve,
        ):
            result = run(update_tools.update_finding(finding_id=UUID_C))
        assert result == "Error: No fields provided to update"
        patch_request.assert_not_called()
        resolve.assert_not_called()

    def test_bad_severity_sends_no_request(self):
        with (
            patch.object(update_tools, "make_patch_request") as patch_request,
            patch.object(resolvers, "resolve_finding_id") as resolve,
        ):
            result = run(
                update_tools.update_finding(finding_id=UUID_C, severity="severe")
            )
        assert result.startswith("Error: invalid severity 'severe'")
        patch_request.assert_not_called()
        resolve.assert_not_called()

    def test_locked_binder_returns_backend_body(self):
        body = '{"non_field_errors": ["Cannot modify the finding when the findings assessment is locked."]}'
        with (
            patch.object(
                update_tools,
                "make_patch_request",
                return_value=_response(400, text=body),
            ),
            patch.object(resolvers, "resolve_finding_id", return_value=UUID_C),
        ):
            result = run(update_tools.update_finding(finding_id=UUID_C, name="New"))
        assert result == f"Error updating finding: 400 - {body}"


# ---------------------------------------------------------------------------
# create_evidence: status and binders
# ---------------------------------------------------------------------------


class TestCreateEvidenceInBinder:
    def _run(self, tmp_path, **kwargs):
        file = tmp_path / "report.png"
        file.write_bytes(PNG_BYTES)
        with (
            patch.object(write_tools, "GLOBAL_FOLDER_ID", None),
            patch.object(write_tools, "resolve_folder_id", return_value=UUID_F),
            patch.object(
                write_tools,
                "make_post_request",
                return_value=_response(201, {"id": UUID_B, "name": "Report"}),
            ) as post,
            patch.object(
                write_tools, "make_upload_request", return_value=_response(200)
            ),
            patch.object(
                write_tools,
                "make_get_request",
                return_value=_response(200, {"attachment": "/media/report.png"}),
            ),
            patch.object(
                resolvers,
                "resolve_findings_assessment_id",
                side_effect=lambda v: f"fa-{v}",
            ),
        ):
            result = run(write_tools.create_evidence(file_path=str(file), **kwargs))
        return result, post

    def test_status_and_binders_in_first_post(self, tmp_path):
        result, post = self._run(
            tmp_path,
            name="Report",
            status="in_review",
            findings_assessments=["Pentest Q4"],
        )
        assert result.startswith(f"Created evidence: Report (ID: {UUID_B})")
        assert post.call_count == 1
        assert post.call_args.args == (
            "/evidences/",
            {
                "name": "Report",
                "status": "in_review",
                "findings_assessments": ["fa-Pentest Q4"],
            },
        )

    def test_payload_unchanged_without_new_parameters(self, tmp_path):
        _, post = self._run(tmp_path, name="Report", folder_id="Security")
        assert post.call_args.args == (
            "/evidences/",
            {"name": "Report", "folder": UUID_F},
        )


# ---------------------------------------------------------------------------
# registration
# ---------------------------------------------------------------------------


def _tool_names(read_only):
    from mcp.server.mcpserver import MCPServer

    fresh = MCPServer("test")
    with (
        patch.object(server, "mcp", fresh),
        patch.object(server, "_registered", False),
    ):
        server.register_tools(read_only=read_only)
        return {t.name for t in asyncio.run(fresh.list_tools())}


def test_new_tools_are_write_tools():
    write_names = {t.__name__ for t in server.WRITE_TOOLS}
    read_names = {t.__name__ for t in server.READ_TOOLS}
    assert NEW_TOOLS <= write_names
    assert not NEW_TOOLS & read_names


def test_new_tools_registered_only_when_writable():
    assert NEW_TOOLS <= _tool_names(read_only=False)
    assert not NEW_TOOLS & _tool_names(read_only=True)
