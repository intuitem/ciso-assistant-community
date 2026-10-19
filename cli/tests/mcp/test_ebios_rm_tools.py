"""Unit tests for the MCP EBIOS RM tools: quotation methods, step ratings, forced values.

Network calls are mocked at their import sites, as in
test_risk_review_tools.py.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp.tools import ebios_rm_tools  # noqa: E402
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

TECHNIQUES = [
    {"id": UUID_C, "ref_id": "T1566", "name": "Phishing"},
    {"id": UUID_D, "ref_id": "T1566.001", "name": "Spearphishing Attachment"},
]


class TestStudyQuotationMethod:
    def test_update_sends_method_and_scoping(self):
        get = Mock(return_value=_response(200, {"quotation_method": "express"}))
        patch_req = Mock(return_value=_response(200, {"id": UUID_A, "name": "S"}))
        with (
            patch.object(ebios_rm_tools, "make_get_request", get),
            patch.object(ebios_rm_tools, "make_patch_request", patch_req),
        ):
            run(
                ebios_rm_tools.update_ebios_rm_study(
                    study_id=UUID_A,
                    quotation_method="advanced",
                    objectives="Obj",
                    constraints_hypotheses="Hyp",
                )
            )
        assert patch_req.call_args.args[1] == {
            "quotation_method": "advanced",
            "objectives": "Obj",
            "constraints_hypotheses": "Hyp",
        }

    def test_create_omits_method_when_not_given(self):
        post = Mock(return_value=_response(201, {"id": UUID_A, "name": "S"}))
        with patch.object(ebios_rm_tools, "make_post_request", post):
            run(
                ebios_rm_tools.create_ebios_rm_study(
                    name="S", folder_id=UUID_F, risk_matrix_id=UUID_B
                )
            )
        assert "quotation_method" not in post.call_args.args[1]


class TestKillChainRatings:
    def test_update_sends_ratings_and_assets(self):
        get = Mock(
            return_value=_response(200, {"elementary_action": {"attack_stage": 2}})
        )
        patch_req = Mock(return_value=_response(200, {"id": UUID_A}))
        with (
            patch.object(ebios_rm_tools, "make_get_request", get),
            patch.object(ebios_rm_tools, "make_patch_request", patch_req),
        ):
            run(
                ebios_rm_tools.update_kill_chain_step(
                    kill_chain_id=UUID_A,
                    success_probability=2,
                    success_probability_pct=40.0,
                    technical_difficulty=1,
                    assets=[UUID_B],
                )
            )
        assert patch_req.call_args.args[1] == {
            "success_probability": 2,
            "success_probability_pct": 40.0,
            "technical_difficulty": 1,
            "assets": [UUID_B],
        }


class TestForcedValues:
    def test_likelihood_forced_set_and_cleared(self):
        patch_req = Mock(return_value=_response(200, {"id": UUID_A}))
        with patch.object(ebios_rm_tools, "make_patch_request", patch_req):
            run(
                ebios_rm_tools.update_operational_scenario(
                    scenario_id=UUID_A, likelihood_forced=3
                )
            )
            assert patch_req.call_args.args[1] == {"likelihood_forced": 3}
            run(
                ebios_rm_tools.update_operational_scenario(
                    scenario_id=UUID_A, likelihood_forced=-1
                )
            )
            assert patch_req.call_args.args[1] == {"likelihood_forced": None}

    def test_gravity_forced_cleared(self):
        patch_req = Mock(return_value=_response(200, {"id": UUID_A, "name": "S"}))
        with patch.object(ebios_rm_tools, "make_patch_request", patch_req):
            run(
                ebios_rm_tools.update_strategic_scenario(
                    scenario_id=UUID_A, gravity_forced=-1
                )
            )
        assert patch_req.call_args.args[1] == {"gravity_forced": None}


class TestTechniques:
    def test_techniques_resolved_by_exact_ref_id(self):
        fake = _router({"/techniques/": TECHNIQUES})
        patch_req = Mock(return_value=_response(200, {"id": UUID_A}))
        with (
            patch.object(ebios_rm_tools, "fetch_all_results", fake),
            patch.object(ebios_rm_tools, "make_patch_request", patch_req),
        ):
            run(
                ebios_rm_tools.update_operational_scenario(
                    scenario_id=UUID_A, techniques=["t1566", UUID_B]
                )
            )
        assert patch_req.call_args.args[1] == {"techniques": [UUID_C, UUID_B]}

    def test_unknown_technique_is_an_error(self):
        fake = _router({"/techniques/": TECHNIQUES})
        post = Mock()
        with (
            patch.object(ebios_rm_tools, "fetch_all_results", fake),
            patch.object(ebios_rm_tools, "make_post_request", post),
        ):
            result = run(
                ebios_rm_tools.create_elementary_action(
                    name="A", folder_id=UUID_F, technique="T9999"
                )
            )
        post.assert_not_called()
        assert "T9999" in result


class TestTargetObjectiveCategory:
    def test_clear_with_empty_string(self):
        patch_req = Mock(return_value=_response(200, {"id": UUID_A}))
        with patch.object(ebios_rm_tools, "make_patch_request", patch_req):
            run(
                ebios_rm_tools.update_ro_to_couple(
                    ro_to_id=UUID_A, target_objective_category=""
                )
            )
        assert patch_req.call_args.args[1] == {"target_objective_category": None}

    def test_resolves_existing_category(self):
        fake = _router(
            {
                "/terminologies/": [
                    {"id": UUID_C, "name": "financial", "translations": {}}
                ]
            }
        )
        patch_req = Mock(return_value=_response(200, {"id": UUID_A}))
        with (
            patch.object(ebios_rm_tools, "fetch_all_results", fake),
            patch.object(ebios_rm_tools, "make_patch_request", patch_req),
        ):
            run(
                ebios_rm_tools.update_ro_to_couple(
                    ro_to_id=UUID_A, target_objective_category="Financial"
                )
            )
        assert patch_req.call_args.args[1] == {"target_objective_category": UUID_C}


class TestOperatingModeQuotation:
    def test_step_roll_up_table(self):
        get = Mock(
            return_value=_response(
                200,
                {
                    "method": "advanced",
                    "likelihood": 2,
                    "steps": {
                        UUID_B: {
                            "probability": 3,
                            "difficulty": 1,
                            "likelihood": 2,
                            "critical": True,
                        }
                    },
                },
            )
        )
        fake = _router(
            {
                "/ebios-rm/kill-chains/": [
                    {"id": UUID_B, "elementary_action": {"str": "Phish admin"}}
                ]
            }
        )
        with (
            patch.object(ebios_rm_tools, "make_get_request", get),
            patch.object(ebios_rm_tools, "fetch_all_results", fake),
        ):
            result = run(ebios_rm_tools.get_operating_mode_quotation(UUID_A))
        assert get.call_args.args[0] == f"/ebios-rm/operating-modes/{UUID_A}/quotation/"
        assert f"|{UUID_B}|Phish admin|3|1|2|Yes|" in result
        assert "Operating mode likelihood: 2" in result

    def test_manual_method_has_no_steps(self):
        get = Mock(return_value=_response(200, {"method": "manual"}))
        with patch.object(ebios_rm_tools, "make_get_request", get):
            result = run(ebios_rm_tools.get_operating_mode_quotation(UUID_A))
        assert "manual" in result and "not computed" in result


class TestMethodChangeGuard:
    def test_leaving_manual_needs_confirmation(self):
        get = Mock(return_value=_response(200, {"quotation_method": "manual"}))
        patch_req = Mock()
        with (
            patch.object(ebios_rm_tools, "make_get_request", get),
            patch.object(ebios_rm_tools, "make_patch_request", patch_req),
        ):
            result = run(
                ebios_rm_tools.update_ebios_rm_study(
                    study_id=UUID_A, quotation_method="standard"
                )
            )
        patch_req.assert_not_called()
        assert "confirm_method_change" in result

    def test_leaving_manual_with_confirmation(self):
        get = Mock()
        patch_req = Mock(return_value=_response(200, {"id": UUID_A, "name": "S"}))
        with (
            patch.object(ebios_rm_tools, "make_get_request", get),
            patch.object(ebios_rm_tools, "make_patch_request", patch_req),
        ):
            run(
                ebios_rm_tools.update_ebios_rm_study(
                    study_id=UUID_A,
                    quotation_method="standard",
                    confirm_method_change=True,
                )
            )
        get.assert_not_called()
        assert patch_req.call_args.args[1] == {"quotation_method": "standard"}

    def test_switch_between_computed_methods_needs_no_confirmation(self):
        get = Mock(return_value=_response(200, {"quotation_method": "express"}))
        patch_req = Mock(return_value=_response(200, {"id": UUID_A, "name": "S"}))
        with (
            patch.object(ebios_rm_tools, "make_get_request", get),
            patch.object(ebios_rm_tools, "make_patch_request", patch_req),
        ):
            run(
                ebios_rm_tools.update_ebios_rm_study(
                    study_id=UUID_A, quotation_method="advanced"
                )
            )
        assert patch_req.call_args.args[1] == {"quotation_method": "advanced"}
