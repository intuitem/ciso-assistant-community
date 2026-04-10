"""Tests for CEL outcome evaluation engine."""

from unittest.mock import patch

import pytest
from core.models import (
    Answer,
    ComplianceAssessment,
    Framework,
    Perimeter,
    Question,
    QuestionChoice,
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
        urn="urn:test:risk:req_node:cel:001",
        ref_id="CEL-001",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    rn2 = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:risk:req_node:cel:002",
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

        ctx, hidden = build_cel_context(cel_setup["ca"])
        assert hidden == set()
        assert ctx["assessment"]["total_count"] == 2
        assert ctx["assessment"]["score_sum"] == 0
        assert ctx["assessment"]["answered_count"] == 0
        assert ctx["assessment"]["score_max"] == 200

        for node_id in ("001", "002"):
            req = ctx["requirements"][node_id]
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

        ctx, _ = build_cel_context(cel_setup["ca"])
        assert ctx["assessment"]["score_sum"] == 80
        assert ctx["assessment"]["answered_count"] == 1
        assert ctx["requirements"]["001"]["score"] == 80

    def test_not_applicable_excluded_from_score_sum(self, cel_setup):
        from core.cel_service import build_cel_context

        ra1 = cel_setup["ra1"]
        ra1.score = 50
        ra1.result = "not_applicable"
        ra1.is_scored = True
        ra1.save(update_fields=["score", "result", "is_scored"])

        ctx, _ = build_cel_context(cel_setup["ca"])
        assert ctx["assessment"]["score_sum"] == 0
        assert ctx["assessment"]["answered_count"] == 0
        assert ctx["requirements"]["001"]["score"] == 0

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
            urn="urn:test:risk:req_node:ig:in",
            ref_id="IG-IN",
            assessable=True,
            implementation_groups=["group_a"],
            folder=folder,
            is_published=True,
        )
        RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:risk:req_node:ig:out",
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

        ctx, _ = build_cel_context(ca)
        assert ctx["assessment"]["total_count"] == 1
        assert "in" in ctx["requirements"]
        assert "out" not in ctx["requirements"]

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
            urn="urn:test:risk:req_node:missing:001",
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
        ctx, _ = build_cel_context(ca)
        assert ctx["assessment"]["total_count"] == 1
        req = ctx["requirements"]["001"]
        assert req["score"] == 0
        assert req["result"] == "not_assessed"
        assert req["status"] == "to_do"

    def test_context_includes_answers(self, cel_setup):
        """Answer data should appear in the CEL context."""
        from core.cel_service import build_cel_context

        rn1 = cel_setup["rn1"]
        ra1 = cel_setup["ra1"]
        folder = cel_setup["folder"]

        q = Question.objects.create(
            requirement_node=rn1,
            urn="urn:test:risk:question:cel:001",
            text="Test question",
            type="unique_choice",
            folder=folder,
        )
        c1 = QuestionChoice.objects.create(
            question=q,
            urn="urn:test:risk:question:cel:001:c:yes",
            value="Yes",
            add_score=80,
            compute_result="true",
            folder=folder,
        )
        answer = Answer.objects.create(
            requirement_assessment=ra1,
            question=q,
            folder=folder,
        )
        answer.selected_choices.add(c1)

        ctx, _ = build_cel_context(cel_setup["ca"])
        assert "answers" in ctx
        assert q.node_id in ctx["answers"]
        ans = ctx["answers"][q.node_id]
        assert ans["score"] == 80  # add_score * weight(1)
        assert ans["type"] == "unique_choice"
        assert "001:c:yes" in ans["selected_choices"]

    def test_context_includes_computed_outcomes(self, cel_setup):
        """Previously computed outcomes should be in the context."""
        from core.cel_service import build_cel_context

        ca = cel_setup["ca"]
        ca.computed_outcome = [{"result": "pass", "label": "High"}]
        ca.save(update_fields=["computed_outcome"])

        ctx, _ = build_cel_context(ca)
        assert ctx["computed_outcomes"] == [{"result": "pass", "label": "High"}]

    def test_empty_answers_dict_when_no_answers(self, cel_setup):
        from core.cel_service import build_cel_context

        ctx, _ = build_cel_context(cel_setup["ca"])
        assert ctx["answers"] == {}


# ---------------------------------------------------------------------------
# TestEvaluateOutcomes
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestEvaluateOutcomes:
    def test_collects_all_matching_outcomes(self, cel_setup):
        """All matching rules should be collected, not just the first."""
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

        # score_sum = 160 >= 150, >= 50, and true all match
        assert isinstance(ca.computed_outcome, list)
        assert len(ca.computed_outcome) == 3
        assert ca.computed_outcome[0] == {"result": "pass", "label": "High"}
        assert ca.computed_outcome[1] == {"result": "partial", "label": "Medium"}
        assert ca.computed_outcome[2] == {"result": "fail", "label": "Low"}
        # expression should not be included
        for outcome in ca.computed_outcome:
            assert "expression" not in outcome

    def test_partial_match(self, cel_setup):
        """Only matching rules should be collected."""
        from core.cel_service import evaluate_outcomes

        ra1 = cel_setup["ra1"]
        ra1.score = 60
        ra1.result = "compliant"
        ra1.is_scored = True
        ra1.save(update_fields=["score", "result", "is_scored"])

        ca = cel_setup["ca"]
        evaluate_outcomes(ca)
        ca.refresh_from_db()

        # score_sum = 60: >= 50 matches, true matches, >= 150 does not
        assert isinstance(ca.computed_outcome, list)
        assert len(ca.computed_outcome) == 2
        assert ca.computed_outcome[0]["result"] == "partial"
        assert ca.computed_outcome[1]["result"] == "fail"

    def test_no_match_sets_empty_list(self, db):
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
        assert ca.computed_outcome == []

    def test_empty_outcomes_definition_clears(self, cel_setup):
        from core.cel_service import evaluate_outcomes

        ca = cel_setup["ca"]
        ca.computed_outcome = [{"stale": True}]
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

        assert ca.computed_outcome == [{"result": "fallback", "label": "OK"}]

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
# TestVisibilityExpression
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestVisibilityExpression:
    def test_visibility_hides_requirement(self, db):
        """A requirement with a false visibility expression should be hidden."""
        from core.cel_service import build_cel_context

        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Vis FW",
            folder=folder,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        rn_visible = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:risk:req_node:vis:visible",
            ref_id="VIS-001",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        rn_hidden = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:risk:req_node:vis:hidden",
            ref_id="VIS-002",
            assessable=True,
            visibility_expression="false",
            folder=folder,
            is_published=True,
        )
        perimeter = Perimeter.objects.create(name="Vis Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Vis CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=rn_visible, folder=folder
        )
        RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=rn_hidden, folder=folder
        )

        ctx, hidden_urns = build_cel_context(ca)

        assert "urn:test:risk:req_node:vis:hidden" in hidden_urns
        assert "urn:test:risk:req_node:vis:visible" not in hidden_urns
        # Hidden requirement excluded from context (keyed by node_id)
        assert "hidden" not in ctx["requirements"]
        assert "visible" in ctx["requirements"]
        assert ctx["assessment"]["total_count"] == 1
        assert ctx["hidden_requirements"] == ["hidden"]

    def test_visibility_no_expression_always_visible(self, cel_setup):
        """Requirements without visibility_expression are always visible."""
        from core.cel_service import build_cel_context

        ctx, hidden_urns = build_cel_context(cel_setup["ca"])
        assert hidden_urns == set()
        assert len(ctx["requirements"]) == 2

    def test_visibility_fail_open(self, db):
        """Invalid visibility expression should keep requirement visible."""
        from core.cel_service import build_cel_context

        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Fail Open FW",
            folder=folder,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:risk:req_node:failopen:001",
            ref_id="FO-001",
            assessable=True,
            visibility_expression="!!!invalid CEL!!!",
            folder=folder,
            is_published=True,
        )
        perimeter = Perimeter.objects.create(name="FO Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="FO CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=fw.requirement_nodes.first(),
            folder=folder,
        )

        ctx, hidden_urns = build_cel_context(ca)
        # Bad expression = fail-open, requirement stays visible
        assert hidden_urns == set()
        assert "001" in ctx["requirements"]

    def test_visibility_based_on_other_requirement_score(self, db):
        """Visibility expression can reference another requirement's score."""
        from core.cel_service import build_cel_context

        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Cross Ref FW",
            folder=folder,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        rn_driver = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:risk:req_node:xref:driver",
            ref_id="XREF-DRIVER",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        rn_dependent = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:risk:req_node:xref:dependent",
            ref_id="XREF-DEP",
            assessable=True,
            visibility_expression='requirements["driver"].score > 50',
            folder=folder,
            is_published=True,
        )
        perimeter = Perimeter.objects.create(name="XRef Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="XRef CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra_driver = RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=rn_driver, folder=folder
        )
        RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=rn_dependent, folder=folder
        )

        # Driver score = 0, dependent should be hidden
        ctx, hidden_urns = build_cel_context(ca)
        assert "urn:test:risk:req_node:xref:dependent" in hidden_urns

        # Set driver score > 50, dependent should become visible
        ra_driver.score = 80
        ra_driver.result = "compliant"
        ra_driver.is_scored = True
        ra_driver.save(update_fields=["score", "result", "is_scored"])

        ctx, hidden_urns = build_cel_context(ca)
        assert "urn:test:risk:req_node:xref:dependent" not in hidden_urns
        assert "dependent" in ctx["requirements"]

    def test_visibility_single_pass_no_cycle(self, db):
        """Circular visibility deps should not cause infinite loops."""
        from core.cel_service import build_cel_context

        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Cycle FW",
            folder=folder,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        rn_a = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:risk:req_node:cycle:a",
            ref_id="CYC-A",
            assessable=True,
            visibility_expression='requirements["b"].score > 50',
            folder=folder,
            is_published=True,
        )
        rn_b = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:risk:req_node:cycle:b",
            ref_id="CYC-B",
            assessable=True,
            visibility_expression='requirements["a"].score > 50',
            folder=folder,
            is_published=True,
        )
        perimeter = Perimeter.objects.create(name="Cyc Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Cyc CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=rn_a, folder=folder
        )
        RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=rn_b, folder=folder
        )

        # This should complete without hanging (single-pass evaluation)
        ctx, hidden_urns = build_cel_context(ca)
        # Both have score 0, both expressions evaluate to false
        # Both should be hidden (single-pass, no re-evaluation)
        assert "urn:test:risk:req_node:cycle:a" in hidden_urns
        assert "urn:test:risk:req_node:cycle:b" in hidden_urns


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
                    urn="urn:test:risk:req_node:cel:new",
                    ref_id="CEL-NEW",
                    assessable=True,
                    folder=cel_setup["folder"],
                    is_published=True,
                ),
                folder=cel_setup["folder"],
            )
            mock_eval.assert_not_called()
