"""Unit tests for the MCP incident tools (create_incident / update_incident).

Network calls and resolvers are mocked at their import sites.
"""

import sys
from pathlib import Path
from unittest.mock import patch


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

GLOBAL = "99999999-9999-9999-9999-999999999999"


class TestCreateIncident:
    def _patch_ok(self):
        return patch.object(
            write_tools,
            "make_post_request",
            return_value=_response(201, {"id": UUID_A, "name": "Phishing"}),
        )

    def test_minimal_defaults_to_global_folder(self):
        with (
            self._patch_ok() as post,
            patch.object(write_tools, "GLOBAL_FOLDER_ID", GLOBAL),
        ):
            result = run(write_tools.create_incident(name="Phishing"))
        assert result == f"Created incident: Phishing (ID: {UUID_A})"
        assert post.call_args.args == (
            "/incidents/",
            {"name": "Phishing", "folder": GLOBAL},
        )

    def test_scalars_only_when_provided(self):
        with (
            self._patch_ok() as post,
            patch.object(write_tools, "GLOBAL_FOLDER_ID", GLOBAL),
        ):
            run(
                write_tools.create_incident(
                    name="Phishing",
                    status="ongoing",
                    severity=1,
                    detection="externally_detected",
                    is_bcp_activated=False,
                )
            )
        assert post.call_args.args[1] == {
            "name": "Phishing",
            "folder": GLOBAL,
            "status": "ongoing",
            "severity": 1,
            "detection": "externally_detected",
            "is_bcp_activated": False,
        }

    def test_names_resolved_and_scoped_to_folder(self):
        with (
            self._patch_ok() as post,
            patch.object(write_tools, "resolve_folder_id", return_value=UUID_F),
            patch.object(
                write_tools, "resolve_asset_id", return_value=UUID_B
            ) as r_asset,
            patch.object(
                write_tools, "resolve_threat_id", return_value=UUID_C
            ) as r_threat,
            patch.object(
                write_tools, "resolve_applied_control_id", return_value=UUID_D
            ) as r_control,
            patch.object(
                write_tools, "resolve_actor_ids", return_value=[UUID_A]
            ) as r_actors,
            patch.object(
                write_tools, "resolve_entity_id", return_value=UUID_B
            ) as r_entity,
            patch.object(
                write_tools, "resolve_qualification_ids", return_value=[UUID_C, UUID_D]
            ) as r_quals,
        ):
            run(
                write_tools.create_incident(
                    name="Phishing",
                    folder_id="Prod",
                    assets=["ERP"],
                    threats=["Phishing"],
                    owners=["a@b.c"],
                    applied_controls=["MFA"],
                    entities=["Acme"],
                    qualifications=["C", "I"],
                )
            )
        r_asset.assert_called_once_with("ERP", folder_id=UUID_F)
        r_threat.assert_called_once_with("Phishing", folder_id=UUID_F)
        r_control.assert_called_once_with("MFA", folder_id=UUID_F)
        r_actors.assert_called_once_with(["a@b.c"])
        r_entity.assert_called_once_with("Acme")
        r_quals.assert_called_once_with(["C", "I"])
        assert post.call_args.args[1] == {
            "name": "Phishing",
            "folder": UUID_F,
            "assets": [UUID_B],
            "threats": [UUID_C],
            "owners": [UUID_A],
            "applied_controls": [UUID_D],
            "entities": [UUID_B],
            "qualifications": [UUID_C, UUID_D],
        }

    def test_resolver_error_is_reported(self):
        with (
            self._patch_ok() as post,
            patch.object(
                write_tools,
                "resolve_asset_id",
                side_effect=ValueError("Asset 'ERP' not found"),
            ),
        ):
            result = run(write_tools.create_incident(name="X", assets=["ERP"]))
        assert result == "Error in create_incident: Asset 'ERP' not found"
        post.assert_not_called()

    def test_backend_rejection_returned(self):
        with patch.object(
            write_tools,
            "make_post_request",
            return_value=_response(400, text='{"occurred_at": ["bad"]}'),
        ):
            result = run(
                write_tools.create_incident(
                    name="X",
                    reported_at="2026-01-01T00:00:00Z",
                    occurred_at="2026-02-01T00:00:00Z",
                )
            )
        assert result == 'Error creating incident: 400 - {"occurred_at": ["bad"]}'


class TestUpdateIncident:
    def _patch_ok(self):
        return patch.object(
            update_tools,
            "make_patch_request",
            return_value=_response(200, {"id": UUID_A, "name": "Phishing"}),
        )

    def test_partial_update_by_name(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(
                update_tools, "resolve_incident_id", return_value=UUID_A
            ) as r_incident,
        ):
            result = run(
                update_tools.update_incident(
                    incident_id="Phishing", status="resolved", resolution="Reset"
                )
            )
        r_incident.assert_called_once_with("Phishing")
        assert result == f"Updated incident: Phishing (ID: {UUID_A})"
        assert patch_req.call_args.args == (
            f"/incidents/{UUID_A}/",
            {"status": "resolved", "resolution": "Reset"},
        )

    def test_name_lookup_uses_search_and_exact_match(self):
        fake = _router(
            {
                "/incidents/": [
                    {"id": UUID_B, "name": "Phishing campaign"},
                    {"id": UUID_C, "name": "Phishing"},
                ]
            }
        )
        with (
            self._patch_ok() as patch_req,
            patch.object(resolvers, "fetch_all_results", side_effect=fake),
        ):
            result = run(
                update_tools.update_incident(incident_id="Phishing", status="closed")
            )
        assert fake.calls == [("/incidents/", {"search": "Phishing"})]
        assert patch_req.call_args.args == (
            f"/incidents/{UUID_C}/",
            {"status": "closed"},
        )
        assert result.startswith("Updated incident:")

    def test_all_relations_in_payload(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(update_tools, "resolve_actor_ids", return_value=[UUID_A]),
            patch.object(
                update_tools, "resolve_qualification_ids", return_value=[UUID_B]
            ),
            patch.object(update_tools, "resolve_entity_id", return_value=UUID_C),
            patch.object(
                update_tools, "resolve_applied_control_id", return_value=UUID_D
            ) as r_control,
        ):
            run(
                update_tools.update_incident(
                    incident_id=UUID_A,
                    owners=["a@b.c"],
                    qualifications=["C"],
                    entities=["Acme"],
                    applied_controls=["MFA"],
                    filtering_labels=[UUID_F],
                )
            )
        r_control.assert_called_once_with("MFA", folder_id=None)
        assert patch_req.call_args.args[1] == {
            "owners": [UUID_A],
            "qualifications": [UUID_B],
            "entities": [UUID_C],
            "applied_controls": [UUID_D],
            "filtering_labels": [UUID_F],
        }

    def test_empty_list_clears_relation(self):
        with self._patch_ok() as patch_req:
            run(update_tools.update_incident(incident_id=UUID_A, owners=[]))
        assert patch_req.call_args.args == (f"/incidents/{UUID_A}/", {"owners": []})

    def test_empty_update_sends_nothing(self):
        with self._patch_ok() as patch_req:
            result = run(update_tools.update_incident(incident_id=UUID_A))
        assert result == "Error: No fields provided to update"
        patch_req.assert_not_called()

    def test_unknown_incident_reported(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(
                update_tools,
                "resolve_incident_id",
                side_effect=ValueError("'Nope' not found at /incidents/"),
            ),
        ):
            result = run(
                update_tools.update_incident(incident_id="Nope", status="closed")
            )
        assert result == "Error in update_incident: 'Nope' not found at /incidents/"
        patch_req.assert_not_called()

    def test_assets_scoped_to_folder_when_given(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(update_tools, "resolve_folder_id", return_value=UUID_F),
            patch.object(
                update_tools, "resolve_asset_id", return_value=UUID_C
            ) as r_asset,
            patch.object(
                update_tools, "resolve_threat_id", return_value=UUID_D
            ) as r_threat,
        ):
            run(
                update_tools.update_incident(
                    incident_id=UUID_A,
                    folder_id="Prod",
                    assets=["ERP"],
                    threats=["Phishing"],
                )
            )
        r_asset.assert_called_once_with("ERP", folder_id=UUID_F)
        r_threat.assert_called_once_with("Phishing", folder_id=UUID_F)
        assert patch_req.call_args.args[1] == {
            "folder": UUID_F,
            "assets": [UUID_C],
            "threats": [UUID_D],
        }

    def test_assets_unscoped_without_folder(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(
                update_tools, "resolve_asset_id", return_value=UUID_C
            ) as r_asset,
        ):
            run(update_tools.update_incident(incident_id=UUID_A, assets=["ERP"]))
        r_asset.assert_called_once_with("ERP", folder_id=None)
        assert patch_req.call_args.args[1] == {"assets": [UUID_C]}

    def test_backend_rejection_returned(self):
        with patch.object(
            update_tools,
            "make_patch_request",
            return_value=_response(400, text="bad status"),
        ):
            result = run(
                update_tools.update_incident(incident_id=UUID_A, status="bogus")
            )
        assert result == "Error updating incident: 400 - bad status"


class TestRegistration:
    def test_incident_tools_are_write_tools(self):
        from ca_mcp import server

        write_names = {t.__name__ for t in server.WRITE_TOOLS}
        read_names = {t.__name__ for t in server.READ_TOOLS}
        assert {"create_incident", "update_incident"} <= write_names
        assert not {"create_incident", "update_incident"} & read_names
