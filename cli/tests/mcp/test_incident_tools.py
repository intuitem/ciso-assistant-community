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
            patch.object(resolvers, "resolve_global_folder_id", return_value=GLOBAL),
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
            patch.object(resolvers, "fetch_all_results", side_effect=fake) as fetch,
        ):
            result = run(
                update_tools.update_incident(incident_id="Phishing", status="closed")
            )
        assert fake.calls == [("/incidents/", {"search": "Phishing"})]
        assert fetch.call_args.kwargs["max_items"] is None
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
            patch.object(
                update_tools,
                "make_get_request",
                return_value=_response(200, {"folder": {"id": UUID_F}}),
            ),
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
        r_control.assert_called_once_with("MFA", folder_id=UUID_F)
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

    def test_assets_scoped_to_incident_folder_without_folder_id(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(
                update_tools, "resolve_asset_id", return_value=UUID_C
            ) as r_asset,
            patch.object(
                update_tools,
                "make_get_request",
                return_value=_response(200, {"folder": {"id": UUID_F}}),
            ) as get,
        ):
            run(update_tools.update_incident(incident_id=UUID_A, assets=["ERP"]))
        get.assert_called_once_with(f"/incidents/{UUID_A}/")
        r_asset.assert_called_once_with("ERP", folder_id=UUID_F)
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


class TestResolveInFolderOrGlobal:
    def test_falls_back_to_global_when_not_found_in_folder(self):
        def resolver(name, folder_id=None):
            if folder_id == UUID_F:
                raise ValueError(f"Threat '{name}' not found")
            return UUID_C

        with patch.object(resolvers, "resolve_global_folder_id", return_value=GLOBAL):
            assert (
                resolvers.resolve_in_folder_or_global(resolver, "Ransomware", UUID_F)
                == UUID_C
            )

    def test_ambiguity_in_folder_is_not_masked(self):
        def resolver(name, folder_id=None):
            raise ValueError(f"Ambiguous asset name '{name}', found 2")

        with patch.object(resolvers, "resolve_global_folder_id", return_value=GLOBAL):
            try:
                resolvers.resolve_in_folder_or_global(resolver, "DB01", UUID_F)
            except ValueError as e:
                assert "Ambiguous" in str(e)
            else:
                raise AssertionError("expected ValueError")

    def test_no_folder_scopes_to_global(self):
        calls = []

        def resolver(name, folder_id=None):
            calls.append(folder_id)
            return UUID_C

        with patch.object(resolvers, "resolve_global_folder_id", return_value=GLOBAL):
            resolvers.resolve_in_folder_or_global(resolver, "DB01")
        assert calls == [GLOBAL]


class TestIncidentTaskTemplates:
    def test_create_resolves_task_templates(self):
        with (
            patch.object(
                write_tools,
                "make_post_request",
                return_value=_response(201, {"id": UUID_A, "name": "X"}),
            ) as post,
            patch.object(
                write_tools, "resolve_task_template_id", side_effect=[UUID_B, UUID_C]
            ) as r_task,
            patch.object(resolvers, "resolve_global_folder_id", return_value=GLOBAL),
        ):
            result = run(
                write_tools.create_incident(
                    name="X", task_templates=["Notify CNIL", UUID_C]
                )
            )
        assert [c.args[0] for c in r_task.call_args_list] == ["Notify CNIL", UUID_C]
        assert post.call_args.args[1]["task_templates"] == [UUID_B, UUID_C]
        assert result.startswith("Created incident:")

    def test_create_omits_empty_task_templates(self):
        with patch.object(
            write_tools,
            "make_post_request",
            return_value=_response(201, {"id": UUID_A, "name": "X"}),
        ) as post:
            run(write_tools.create_incident(name="X", task_templates=[]))
        assert "task_templates" not in post.call_args.args[1]

    def test_create_resolver_error_reported(self):
        with (
            patch.object(write_tools, "make_post_request") as post,
            patch.object(
                write_tools,
                "resolve_task_template_id",
                side_effect=ValueError("Task template 'Nope' not found"),
            ),
            patch.object(resolvers, "resolve_global_folder_id", return_value=GLOBAL),
        ):
            result = run(write_tools.create_incident(name="X", task_templates=["Nope"]))
        assert result == "Error in create_incident: Task template 'Nope' not found"
        post.assert_not_called()

    def _patch_incident_folder(self):
        return patch.object(
            update_tools,
            "make_get_request",
            return_value=_response(200, {"folder": {"id": UUID_F}}),
        )

    def _patch_update_ok(self):
        return patch.object(
            update_tools,
            "make_patch_request",
            return_value=_response(200, {"id": UUID_A, "name": "X"}),
        )

    def test_update_replaces_task_templates(self):
        with (
            self._patch_update_ok() as patch_req,
            patch.object(
                update_tools, "resolve_task_template_id", return_value=UUID_B
            ) as r_task,
            self._patch_incident_folder(),
        ):
            run(
                update_tools.update_incident(
                    incident_id=UUID_A, task_templates=["Notify CNIL"]
                )
            )
        r_task.assert_called_once_with("Notify CNIL", folder_id=UUID_F)
        assert patch_req.call_args.args == (
            f"/incidents/{UUID_A}/",
            {"task_templates": [UUID_B]},
        )

    def test_update_empty_list_clears_task_templates(self):
        with self._patch_update_ok() as patch_req:
            run(update_tools.update_incident(incident_id=UUID_A, task_templates=[]))
        assert patch_req.call_args.args == (
            f"/incidents/{UUID_A}/",
            {"task_templates": []},
        )

    def test_update_resolver_error_reported(self):
        with (
            self._patch_update_ok() as patch_req,
            patch.object(
                update_tools,
                "resolve_task_template_id",
                side_effect=ValueError("Task template 'Nope' not found"),
            ),
            self._patch_incident_folder(),
            patch.object(resolvers, "resolve_global_folder_id", return_value=GLOBAL),
        ):
            result = run(
                update_tools.update_incident(
                    incident_id=UUID_A, task_templates=["Nope"]
                )
            )
        assert result == "Error in update_incident: Task template 'Nope' not found"
        patch_req.assert_not_called()


class TestResolveTaskTemplateId:
    def test_uuid_returned_without_lookup(self):
        with patch.object(resolvers, "fetch_all_results") as fetch:
            assert resolvers.resolve_task_template_id(UUID_A) == UUID_A
        fetch.assert_not_called()

    def test_name_lookup_uses_search_and_exact_match(self):
        fake = _router(
            {
                "/task-templates/": [
                    {"id": UUID_B, "name": "Notify CNIL"},
                    {"id": UUID_C, "name": "Notify"},
                ]
            }
        )
        with patch.object(resolvers, "fetch_all_results", side_effect=fake) as fetch:
            assert resolvers.resolve_task_template_id("Notify") == UUID_C
        assert fake.calls == [("/task-templates/", {"search": "Notify"})]
        assert fetch.call_args.kwargs["max_items"] is None

    def test_match_ignores_case_and_whitespace(self):
        fake = _router({"/task-templates/": [{"id": UUID_B, "name": "Notify CNIL"}]})
        with patch.object(resolvers, "fetch_all_results", side_effect=fake):
            assert resolvers.resolve_task_template_id(" notify cnil ") == UUID_B

    def test_folder_scopes_search(self):
        fake = _router({"/task-templates/": [{"id": UUID_B, "name": "Notify"}]})
        with patch.object(resolvers, "fetch_all_results", side_effect=fake):
            resolvers.resolve_task_template_id("Notify", folder_id=UUID_F)
        assert fake.calls == [
            ("/task-templates/", {"search": "Notify", "folder": UUID_F})
        ]

    def test_no_exact_match_is_not_found(self):
        fake = _router({"/task-templates/": [{"id": UUID_B, "name": "Notify CNIL"}]})
        with patch.object(resolvers, "fetch_all_results", side_effect=fake):
            try:
                resolvers.resolve_task_template_id("Notify")
            except ValueError as e:
                assert str(e) == "Task template 'Notify' not found"
            else:
                raise AssertionError("expected ValueError")

    def test_duplicate_exact_names_are_ambiguous(self):
        fake = _router(
            {
                "/task-templates/": [
                    {"id": UUID_B, "name": "Notify"},
                    {"id": UUID_C, "name": "Notify"},
                ]
            }
        )
        with patch.object(resolvers, "fetch_all_results", side_effect=fake):
            try:
                resolvers.resolve_task_template_id("Notify")
            except ValueError as e:
                assert str(e) == "Ambiguous task template name 'Notify', found 2"
            else:
                raise AssertionError("expected ValueError")

    def test_api_error_reported(self):
        with patch.object(
            resolvers, "fetch_all_results", return_value=(None, "500 boom")
        ):
            try:
                resolvers.resolve_task_template_id("Notify")
            except ValueError as e:
                assert str(e) == "Task template 'Notify' API error: 500 boom"
            else:
                raise AssertionError("expected ValueError")
