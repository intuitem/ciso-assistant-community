"""Tests for CEL outcome evaluation engine."""

from unittest.mock import patch

import pytest
from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from iam.models import Folder


@pytest.fixture
def cel_setup(db):
    """Framework with two assessable nodes and a compliance assessment."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="CEL Test Framework",
        folder=folder,
        is_published=True,
        min_score=0,
        max_score=100,
        outcomes_definition=[
            {
                "expression": "assessment.score_sum >= 150",
                "result": "pass",
                "label": "High",
            },
            {
                "expression": "assessment.score_sum >= 50",
                "result": "partial",
                "label": "Medium",
            },
            {
                "expression": "true",
                "result": "fail",
                "label": "Low",
            },
        ],
    )
    rn1 = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:cel:req:001",
        ref_id="CEL-001",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    rn2 = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:cel:req:002",
        ref_id="CEL-002",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    perimeter = Perimeter.objects.create(name="CEL Perim", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="CEL CA",
        framework=fw,
        folder=folder,
        perimeter=perimeter,
        is_published=True,
        min_score=0,
        max_score=100,
    )
    RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=rn1,
        folder=folder,
    )
    RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=rn2,
        folder=folder,
    )
    # Re-fetch so from_db sets _loaded_cel_values for change detection
    ra1 = RequirementAssessment.objects.get(compliance_assessment=ca, requirement=rn1)
    ra2 = RequirementAssessment.objects.get(compliance_assessment=ca, requirement=rn2)
    return {
        "framework": fw,
        "ca": ca,
        "rn1": rn1,
        "rn2": rn2,
        "ra1": ra1,
        "ra2": ra2,
        "folder": folder,
    }


# ---------------------------------------------------------------------------
# TestBuildCelContext
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestBuildCelContext:
    def test_zero_fill_defaults(self, cel_setup):
        from core.cel_service import build_cel_context

        ctx = build_cel_context(cel_setup["ca"])
        assert ctx["assessment"]["total_count"] == 2
        assert ctx["assessment"]["score_sum"] == 0
        assert ctx["assessment"]["answered_count"] == 0
        assert ctx["assessment"]["score_max"] == 200

        for urn in ("urn:test:cel:req:001", "urn:test:cel:req:002"):
            req = ctx["requirements"][urn]
            assert req["score"] == 0
            assert req["result"] == "not_assessed"
            assert req["status"] == "to_do"

    def test_scored_requirements(self, cel_setup):
        from core.cel_service import build_cel_context

        ra1 = cel_setup["ra1"]
        ra1.score = 80
        ra1.result = "compliant"
        ra1.is_scored = True
        ra1.save(update_fields=["score", "result", "is_scored"])

        ctx = build_cel_context(cel_setup["ca"])
        assert ctx["assessment"]["score_sum"] == 80
        assert ctx["assessment"]["answered_count"] == 1
        assert ctx["requirements"]["urn:test:cel:req:001"]["score"] == 80

    def test_not_applicable_excluded_from_score_sum(self, cel_setup):
        from core.cel_service import build_cel_context

        ra1 = cel_setup["ra1"]
        ra1.score = 50
        ra1.result = "not_applicable"
        ra1.is_scored = True
        ra1.save(update_fields=["score", "result", "is_scored"])

        ctx = build_cel_context(cel_setup["ca"])
        assert ctx["assessment"]["score_sum"] == 0
        assert ctx["assessment"]["answered_count"] == 0
        assert ctx["requirements"]["urn:test:cel:req:001"]["score"] == 0

    def test_implementation_groups_filtering(self, db):
        from core.cel_service import build_cel_context

        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="IG Framework",
            folder=folder,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        rn_in = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:ig:in",
            ref_id="IG-IN",
            assessable=True,
            implementation_groups=["group_a"],
            folder=folder,
            is_published=True,
        )
        RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:ig:out",
            ref_id="IG-OUT",
            assessable=True,
            implementation_groups=["group_b"],
            folder=folder,
            is_published=True,
        )
        perimeter = Perimeter.objects.create(name="IG Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="IG CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
            selected_implementation_groups=["group_a"],
        )
        RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=rn_in, folder=folder
        )

        ctx = build_cel_context(ca)
        assert ctx["assessment"]["total_count"] == 1
        assert "urn:test:ig:in" in ctx["requirements"]
        assert "urn:test:ig:out" not in ctx["requirements"]

    def test_missing_ra_for_node(self, db):
        from core.cel_service import build_cel_context

        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Missing RA Framework",
            folder=folder,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:missing:001",
            ref_id="MISS-001",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        perimeter = Perimeter.objects.create(name="Miss Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Miss CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        # No RA created for the node
        ctx = build_cel_context(ca)
        assert ctx["assessment"]["total_count"] == 1
        req = ctx["requirements"]["urn:test:missing:001"]
        assert req["score"] == 0
        assert req["result"] == "not_assessed"
        assert req["status"] == "to_do"


# ---------------------------------------------------------------------------
# TestEvaluateOutcomes
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestEvaluateOutcomes:
    def test_first_match_wins(self, cel_setup):
        from core.cel_service import evaluate_outcomes

        ra1, ra2 = cel_setup["ra1"], cel_setup["ra2"]
        ra1.score = 80
        ra1.result = "compliant"
        ra1.is_scored = True
        ra1.save(update_fields=["score", "result", "is_scored"])
        ra2.score = 80
        ra2.result = "compliant"
        ra2.is_scored = True
        ra2.save(update_fields=["score", "result", "is_scored"])

        ca = cel_setup["ca"]
        evaluate_outcomes(ca)
        ca.refresh_from_db()

        assert ca.computed_outcome == {"result": "pass", "label": "High"}
        assert "expression" not in ca.computed_outcome

    def test_second_rule_match(self, cel_setup):
        from core.cel_service import evaluate_outcomes

        ra1 = cel_setup["ra1"]
        ra1.score = 60
        ra1.result = "compliant"
        ra1.is_scored = True
        ra1.save(update_fields=["score", "result", "is_scored"])

        ca = cel_setup["ca"]
        evaluate_outcomes(ca)
        ca.refresh_from_db()

        assert ca.computed_outcome["result"] == "partial"

    def test_no_match_sets_none(self, db):
        from core.cel_service import evaluate_outcomes

        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="No Match FW",
            folder=folder,
            is_published=True,
            min_score=0,
            max_score=100,
            outcomes_definition=[
                {"expression": "false", "result": "never"},
            ],
        )
        perimeter = Perimeter.objects.create(name="NM Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="No Match CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        evaluate_outcomes(ca)
        ca.refresh_from_db()
        assert ca.computed_outcome is None

    def test_empty_outcomes_definition(self, cel_setup):
        from core.cel_service import evaluate_outcomes

        ca = cel_setup["ca"]
        ca.computed_outcome = {"stale": True}
        ca.save(update_fields=["computed_outcome"])

        ca.framework.outcomes_definition = []
        ca.framework.save(update_fields=["outcomes_definition"])

        evaluate_outcomes(ca)
        ca.refresh_from_db()
        assert ca.computed_outcome is None

    def test_bad_expression_logged_and_skipped(self, cel_setup):
        from core.cel_service import evaluate_outcomes

        fw = cel_setup["framework"]
        fw.outcomes_definition = [
            {"expression": "!!!bad syntax!!!", "result": "broken"},
            {"expression": "true", "result": "fallback", "label": "OK"},
        ]
        fw.save(update_fields=["outcomes_definition"])

        ca = cel_setup["ca"]
        evaluate_outcomes(ca)
        ca.refresh_from_db()

        assert ca.computed_outcome == {"result": "fallback", "label": "OK"}

    def test_no_save_when_outcome_unchanged(self, cel_setup):
        from core.cel_service import evaluate_outcomes

        ca = cel_setup["ca"]
        # First evaluation sets outcome
        evaluate_outcomes(ca)
        ca.refresh_from_db()
        first_outcome = ca.computed_outcome

        with patch.object(ComplianceAssessment, "save", wraps=ca.save) as mock_save:
            evaluate_outcomes(ca)
            # save should NOT have been called since outcome didn't change
            mock_save.assert_not_called()

        ca.refresh_from_db()
        assert ca.computed_outcome == first_outcome


# ---------------------------------------------------------------------------
# TestCelTrigger
# ---------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
class TestCelTrigger:
    def test_trigger_fires_on_score_change(self, cel_setup):
        ra1 = cel_setup["ra1"]
        ca = cel_setup["ca"]

        ra1.score = 60
        ra1.result = "compliant"
        ra1.is_scored = True
        ra1.save(update_fields=["score", "result", "is_scored"])

        ca.refresh_from_db()
        assert ca.computed_outcome is not None

    def test_no_trigger_on_irrelevant_field(self, cel_setup):
        ra1 = cel_setup["ra1"]
        ca = cel_setup["ca"]

        with patch("core.cel_service.evaluate_outcomes") as mock_eval:
            ra1.observation = "just a note"
            ra1.save(update_fields=["observation"])
            mock_eval.assert_not_called()

    def test_deduplication_per_ca(self, cel_setup):
        from django.db import transaction as txn

        ra1, ra2 = cel_setup["ra1"], cel_setup["ra2"]

        with patch("core.cel_service.evaluate_outcomes") as mock_eval:
            with txn.atomic():
                ra1.score = 10
                ra1.result = "compliant"
                ra1.is_scored = True
                ra1.save(update_fields=["score", "result", "is_scored"])

                ra2.score = 20
                ra2.result = "compliant"
                ra2.is_scored = True
                ra2.save(update_fields=["score", "result", "is_scored"])

            # on_commit fires after atomic block
            assert mock_eval.call_count == 1

    def test_new_instance_no_trigger(self, cel_setup):
        ca = cel_setup["ca"]

        with patch("core.cel_service.evaluate_outcomes") as mock_eval:
            RequirementAssessment.objects.create(
                compliance_assessment=ca,
                requirement=RequirementNode.objects.create(
                    framework=cel_setup["framework"],
                    urn="urn:test:cel:req:new",
                    ref_id="CEL-NEW",
                    assessable=True,
                    folder=cel_setup["folder"],
                    is_published=True,
                ),
                folder=cel_setup["folder"],
            )
            mock_eval.assert_not_called()
