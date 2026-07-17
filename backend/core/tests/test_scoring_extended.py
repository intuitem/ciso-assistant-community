"""Extended tests for scoring logic and visibility (depends_on) edge cases."""

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
def scoring_setup(db):
    """Set up a framework with two scored questions for testing edge cases."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Extended Scoring FW",
        folder=folder,
        is_published=True,
        min_score=0,
        max_score=100,
    )
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:extscore:req:001",
        ref_id="EXT-REQ",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    # Q1: single choice
    q1 = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:eq1",
        ref_id="EQ1",
        text="Question 1",
        type=Question.Type.UNIQUE_CHOICE,
        order=0,
        weight=1,
        folder=folder,
        is_published=True,
    )
    q1_good = QuestionChoice.objects.create(
        question=q1,
        urn="urn:test:choice:eq1:ec1a",
        ref_id="EC1A",
        value="Good",
        add_score=10,
        compute_result="true",
        order=0,
        folder=folder,
        is_published=True,
    )
    q1_bad = QuestionChoice.objects.create(
        question=q1,
        urn="urn:test:choice:eq1:ec1b",
        ref_id="EC1B",
        value="Bad",
        add_score=0,
        compute_result="false",
        order=1,
        folder=folder,
        is_published=True,
    )

    # Q2: single choice
    q2 = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:eq2",
        ref_id="EQ2",
        text="Question 2",
        type=Question.Type.UNIQUE_CHOICE,
        order=1,
        weight=1,
        folder=folder,
        is_published=True,
    )
    q2_good = QuestionChoice.objects.create(
        question=q2,
        urn="urn:test:choice:eq2:ec2a",
        ref_id="EC2A",
        value="Good",
        add_score=10,
        compute_result="true",
        order=0,
        folder=folder,
        is_published=True,
    )
    q2_bad = QuestionChoice.objects.create(
        question=q2,
        urn="urn:test:choice:eq2:ec2b",
        ref_id="EC2B",
        value="Bad",
        add_score=0,
        compute_result="false",
        order=1,
        folder=folder,
        is_published=True,
    )

    perimeter = Perimeter.objects.create(name="Ext Perim", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="Ext CA",
        framework=fw,
        folder=folder,
        perimeter=perimeter,
        is_published=True,
        min_score=0,
        max_score=100,
    )
    ra = RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=rn,
        folder=folder,
    )
    return {
        "framework": fw,
        "requirement_node": rn,
        "q1": q1,
        "q1_good": q1_good,
        "q1_bad": q1_bad,
        "q2": q2,
        "q2_good": q2_good,
        "q2_bad": q2_bad,
        "ca": ca,
        "ra": ra,
        "folder": folder,
        "perimeter": perimeter,
    }


@pytest.mark.django_db
class TestScoringExtended:
    def test_partially_compliant_result(self, scoring_setup):
        """Two questions: one true, one false -> partially_compliant."""
        d = scoring_setup
        a1 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q1"], folder=d["folder"]
        )
        a1.selected_choices.set([d["q1_good"]])  # compute_result="true"

        a2 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q2"], folder=d["folder"]
        )
        a2.selected_choices.set([d["q2_bad"]])  # compute_result="false"

        d["ra"].compute_score_and_result()
        d["ra"].refresh_from_db()

        assert d["ra"].result == "partially_compliant"

    def test_sum_aggregation_mode(self, scoring_setup):
        """SUM calculation method: score = raw sum, not divided by weight."""
        d = scoring_setup
        d["ca"].score_calculation_method = ComplianceAssessment.CalculationMethod.SUM
        d["ca"].save(update_fields=["score_calculation_method"])

        a1 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q1"], folder=d["folder"]
        )
        a1.selected_choices.set([d["q1_good"]])  # add_score=10, weight=1

        a2 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q2"], folder=d["folder"]
        )
        a2.selected_choices.set([d["q2_good"]])  # add_score=10, weight=1

        d["ra"].compute_score_and_result()
        d["ra"].refresh_from_db()

        # SUM: total_score = 10*1 + 10*1 = 20 (not divided by weight)
        assert d["ra"].score == 20

    def test_sum_aggregation_via_scores_definition(self, scoring_setup):
        """scores_definition.aggregation takes precedence over score_calculation_method."""
        d = scoring_setup
        # Set calculation method to AVG, but scores_definition overrides to sum
        d["ca"].score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        d["ca"].scores_definition = {"aggregation": "sum"}
        d["ca"].save(update_fields=["score_calculation_method", "scores_definition"])

        a1 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q1"], folder=d["folder"]
        )
        a1.selected_choices.set([d["q1_good"]])  # add_score=10

        a2 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q2"], folder=d["folder"]
        )
        a2.selected_choices.set([d["q2_good"]])  # add_score=10

        d["ra"].compute_score_and_result()
        d["ra"].refresh_from_db()

        # scores_definition aggregation "sum" overrides AVG -> raw sum = 20
        assert d["ra"].score == 20

    def test_score_clamped_to_min_max(self, db):
        """Score clamped to max_score and min_score."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Clamp FW",
            folder=folder,
            is_published=True,
            min_score=0,
            max_score=50,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:clamp:req:001",
            ref_id="CL-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:clq1",
            ref_id="CLQ1",
            type=Question.Type.UNIQUE_CHOICE,
            order=0,
            weight=1,
            folder=folder,
            is_published=True,
        )
        c_high = QuestionChoice.objects.create(
            question=q,
            urn="urn:test:choice:clq1:clc1",
            ref_id="CLC1",
            value="Very high",
            add_score=100,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            urn="urn:test:choice:clq1:clc2",
            ref_id="CLC2",
            value="Placeholder",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Clamp Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Clamp CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=50,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=rn, folder=folder
        )

        answer = Answer.objects.create(
            requirement_assessment=ra, question=q, folder=folder
        )
        answer.selected_choices.set([c_high])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        assert ra.score == 50  # clamped to max_score

    def test_answered_question_with_no_score_no_result(self, scoring_setup):
        """Choice with add_score=None, compute_result=None -> no crash."""
        d = scoring_setup
        # Remove score/result from q1's choices
        d["q1_good"].add_score = None
        d["q1_good"].compute_result = None
        d["q1_good"].save()
        d["q1_bad"].add_score = None
        d["q1_bad"].compute_result = None
        d["q1_bad"].save()
        # Also for q2
        d["q2_good"].add_score = None
        d["q2_good"].compute_result = None
        d["q2_good"].save()
        d["q2_bad"].add_score = None
        d["q2_bad"].compute_result = None
        d["q2_bad"].save()

        a1 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q1"], folder=d["folder"]
        )
        a1.selected_choices.set([d["q1_good"]])

        a2 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q2"], folder=d["folder"]
        )
        a2.selected_choices.set([d["q2_good"]])

        # Set a non-default result to prove compute_score_and_result leaves the
        # manual result alone when the requirement is not compute_result-driven
        # (no choice has a resolvable compute_result).
        d["ra"].result = "compliant"
        d["ra"].is_scored = True
        d["ra"].save(update_fields=["result", "is_scored"])

        d["ra"].compute_score_and_result()
        d["ra"].refresh_from_db()

        # No crash; the requirement isn't result-driven, so the auditor-set
        # result is preserved. Score is still recomputed (and falls back to
        # None / is_scored=False since no choice carries add_score either).
        assert d["ra"].result == "compliant"
        assert d["ra"].is_scored is False
        assert d["ra"].score is None

    def test_score_only_no_result_fields(self, scoring_setup):
        """Choices with add_score but compute_result=None -> only score+is_scored saved."""
        d = scoring_setup
        # Set choices to score-only
        for c in [d["q1_good"], d["q1_bad"], d["q2_good"], d["q2_bad"]]:
            c.compute_result = None
            c.save()

        a1 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q1"], folder=d["folder"]
        )
        a1.selected_choices.set([d["q1_good"]])  # add_score=10

        a2 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q2"], folder=d["folder"]
        )
        a2.selected_choices.set([d["q2_good"]])  # add_score=10

        d["ra"].compute_score_and_result()
        d["ra"].refresh_from_db()

        assert d["ra"].is_scored is True
        assert d["ra"].score == 10  # mean: (10+10)/2

    def test_result_only_no_score_fields(self, scoring_setup):
        """Choices with compute_result but add_score=None -> only result saved."""
        d = scoring_setup
        for c in [d["q1_good"], d["q1_bad"], d["q2_good"], d["q2_bad"]]:
            c.add_score = None
            c.save()

        a1 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q1"], folder=d["folder"]
        )
        a1.selected_choices.set([d["q1_good"]])  # compute_result="true"

        a2 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q2"], folder=d["folder"]
        )
        a2.selected_choices.set([d["q2_good"]])  # compute_result="true"

        d["ra"].compute_score_and_result()
        d["ra"].refresh_from_db()

        assert d["ra"].result == "compliant"
        assert d["ra"].is_scored is False
        assert d["ra"].score is None


@pytest.mark.django_db
class TestSemanticComputeResult:
    """Aggregation of semantic compute_result values and legacy true/false literals."""

    def _build_two_question_ra(
        self, folder, q1_choices, q2_choices, q1_type=None, q2_type=None
    ):
        """Build a framework with two questions and the supplied choice specs.

        Each entry of q1_choices/q2_choices is a dict with keys: ref_id, value,
        compute_result (str | None), add_score (int | None).
        """
        from core.models import (
            ComplianceAssessment,
            Framework,
            Perimeter,
            Question,
            QuestionChoice,
            RequirementAssessment,
            RequirementNode,
        )

        suffix = f"{id(q1_choices)}-{id(q2_choices)}"
        fw = Framework.objects.create(
            name=f"Sem FW {suffix}",
            folder=folder,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn=f"urn:test:sem:{suffix}:req:001",
            ref_id="SEM-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )

        def _make_question(idx, q_type, choices_spec):
            q = Question.objects.create(
                requirement_node=rn,
                urn=f"urn:test:sem:{suffix}:q{idx}",
                ref_id=f"SQ{idx}",
                type=q_type or Question.Type.UNIQUE_CHOICE,
                order=idx,
                weight=1,
                folder=folder,
                is_published=True,
            )
            created = []
            for i, spec in enumerate(choices_spec):
                created.append(
                    QuestionChoice.objects.create(
                        question=q,
                        urn=f"urn:test:sem:{suffix}:q{idx}:c{i}",
                        ref_id=spec["ref_id"],
                        value=spec["value"],
                        add_score=spec.get("add_score"),
                        compute_result=spec.get("compute_result"),
                        order=i,
                        folder=folder,
                        is_published=True,
                    )
                )
            return q, created

        q1, q1_choice_objs = _make_question(1, q1_type, q1_choices)
        q2, q2_choice_objs = _make_question(2, q2_type, q2_choices)

        perimeter = Perimeter.objects.create(name=f"Sem Perim {suffix}", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name=f"Sem CA {suffix}",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=rn, folder=folder
        )
        return ra, q1, q1_choice_objs, q2, q2_choice_objs

    def test_non_compliant_choice_yields_non_compliant_result(self, db):
        """A 'non_compliant' choice on every question -> requirement is non_compliant."""
        folder = Folder.get_root_folder()
        ra, q1, q1_choices, q2, q2_choices = self._build_two_question_ra(
            folder,
            q1_choices=[
                {
                    "ref_id": "A",
                    "value": "Non-compliant",
                    "compute_result": "non_compliant",
                },
                {"ref_id": "B", "value": "Compliant", "compute_result": "compliant"},
            ],
            q2_choices=[
                {
                    "ref_id": "C",
                    "value": "Non-compliant",
                    "compute_result": "non_compliant",
                },
                {"ref_id": "D", "value": "Compliant", "compute_result": "compliant"},
            ],
        )

        a1 = Answer.objects.create(
            requirement_assessment=ra, question=q1, folder=folder
        )
        a1.selected_choices.set([q1_choices[0]])  # non_compliant
        a2 = Answer.objects.create(
            requirement_assessment=ra, question=q2, folder=folder
        )
        a2.selected_choices.set([q2_choices[0]])  # non_compliant

        ra.compute_score_and_result()
        ra.refresh_from_db()

        assert ra.result == "non_compliant"

    def test_all_compliant_choices_yield_compliant(self, db):
        folder = Folder.get_root_folder()
        ra, q1, q1_choices, q2, q2_choices = self._build_two_question_ra(
            folder,
            q1_choices=[
                {"ref_id": "A", "value": "OK", "compute_result": "compliant"},
                {"ref_id": "B", "value": "KO", "compute_result": "non_compliant"},
            ],
            q2_choices=[
                {"ref_id": "C", "value": "OK", "compute_result": "compliant"},
                {"ref_id": "D", "value": "KO", "compute_result": "non_compliant"},
            ],
        )
        a1 = Answer.objects.create(
            requirement_assessment=ra, question=q1, folder=folder
        )
        a1.selected_choices.set([q1_choices[0]])
        a2 = Answer.objects.create(
            requirement_assessment=ra, question=q2, folder=folder
        )
        a2.selected_choices.set([q2_choices[0]])

        ra.compute_score_and_result()
        ra.refresh_from_db()
        assert ra.result == "compliant"

    def test_mixed_compliant_and_non_compliant_yields_partial(self, db):
        folder = Folder.get_root_folder()
        ra, q1, q1_choices, q2, q2_choices = self._build_two_question_ra(
            folder,
            q1_choices=[
                {"ref_id": "A", "value": "OK", "compute_result": "compliant"},
                {"ref_id": "B", "value": "KO", "compute_result": "non_compliant"},
            ],
            q2_choices=[
                {"ref_id": "C", "value": "OK", "compute_result": "compliant"},
                {"ref_id": "D", "value": "KO", "compute_result": "non_compliant"},
            ],
        )
        a1 = Answer.objects.create(
            requirement_assessment=ra, question=q1, folder=folder
        )
        a1.selected_choices.set([q1_choices[0]])  # compliant
        a2 = Answer.objects.create(
            requirement_assessment=ra, question=q2, folder=folder
        )
        a2.selected_choices.set([q2_choices[1]])  # non_compliant

        ra.compute_score_and_result()
        ra.refresh_from_db()
        assert ra.result == "partially_compliant"

    def test_partially_compliant_choice_yields_partial(self, db):
        """A single 'partially_compliant' choice on its own propagates to the requirement."""
        folder = Folder.get_root_folder()
        ra, q1, q1_choices, q2, q2_choices = self._build_two_question_ra(
            folder,
            q1_choices=[
                {
                    "ref_id": "A",
                    "value": "Mid",
                    "compute_result": "partially_compliant",
                },
            ],
            q2_choices=[
                {"ref_id": "B", "value": "OK", "compute_result": "compliant"},
            ],
        )
        a1 = Answer.objects.create(
            requirement_assessment=ra, question=q1, folder=folder
        )
        a1.selected_choices.set([q1_choices[0]])
        a2 = Answer.objects.create(
            requirement_assessment=ra, question=q2, folder=folder
        )
        a2.selected_choices.set([q2_choices[0]])

        ra.compute_score_and_result()
        ra.refresh_from_db()
        assert ra.result == "partially_compliant"

    def test_not_applicable_choice_is_neutral_in_mix(self, db):
        """A 'not_applicable' choice is dropped from the pool; other contributions decide."""
        folder = Folder.get_root_folder()
        ra, q1, q1_choices, q2, q2_choices = self._build_two_question_ra(
            folder,
            q1_choices=[
                {"ref_id": "A", "value": "N/A", "compute_result": "not_applicable"},
            ],
            q2_choices=[
                {"ref_id": "B", "value": "KO", "compute_result": "non_compliant"},
            ],
        )
        a1 = Answer.objects.create(
            requirement_assessment=ra, question=q1, folder=folder
        )
        a1.selected_choices.set([q1_choices[0]])
        a2 = Answer.objects.create(
            requirement_assessment=ra, question=q2, folder=folder
        )
        a2.selected_choices.set([q2_choices[0]])

        ra.compute_score_and_result()
        ra.refresh_from_db()
        assert ra.result == "non_compliant"

    def test_null_compute_result_stays_neutral(self, db):
        """A choice with compute_result=None does not contribute to the result."""
        folder = Folder.get_root_folder()
        ra, q1, q1_choices, q2, q2_choices = self._build_two_question_ra(
            folder,
            q1_choices=[
                {"ref_id": "A", "value": "Neutral", "compute_result": None},
            ],
            q2_choices=[
                {"ref_id": "B", "value": "OK", "compute_result": "compliant"},
            ],
        )
        a1 = Answer.objects.create(
            requirement_assessment=ra, question=q1, folder=folder
        )
        a1.selected_choices.set([q1_choices[0]])
        a2 = Answer.objects.create(
            requirement_assessment=ra, question=q2, folder=folder
        )
        a2.selected_choices.set([q2_choices[0]])

        ra.compute_score_and_result()
        ra.refresh_from_db()
        # Null compute_result is neutral (not a veto) -> overall result follows q2
        assert ra.result == "compliant"

    def test_all_not_applicable_yields_not_applicable(self, db):
        folder = Folder.get_root_folder()
        ra, q1, q1_choices, q2, q2_choices = self._build_two_question_ra(
            folder,
            q1_choices=[
                {"ref_id": "A", "value": "N/A", "compute_result": "not_applicable"},
            ],
            q2_choices=[
                {"ref_id": "B", "value": "N/A", "compute_result": "not_applicable"},
            ],
        )
        a1 = Answer.objects.create(
            requirement_assessment=ra, question=q1, folder=folder
        )
        a1.selected_choices.set([q1_choices[0]])
        a2 = Answer.objects.create(
            requirement_assessment=ra, question=q2, folder=folder
        )
        a2.selected_choices.set([q2_choices[0]])

        ra.compute_score_and_result()
        ra.refresh_from_db()
        assert ra.result == "not_applicable"

    def test_multiple_choice_one_to_one_mapping(self, db):
        """Each ticked choice on a multi-choice question contributes one result."""
        folder = Folder.get_root_folder()
        ra, q1, q1_choices, q2, q2_choices = self._build_two_question_ra(
            folder,
            q1_choices=[
                {"ref_id": "A", "value": "OK", "compute_result": "compliant"},
                {"ref_id": "B", "value": "KO", "compute_result": "non_compliant"},
                {
                    "ref_id": "C",
                    "value": "Mid",
                    "compute_result": "partially_compliant",
                },
            ],
            q2_choices=[
                {"ref_id": "D", "value": "OK", "compute_result": "compliant"},
            ],
            q1_type=Question.Type.MULTIPLE_CHOICE,
        )
        a1 = Answer.objects.create(
            requirement_assessment=ra, question=q1, folder=folder
        )
        # Select compliant + non_compliant on the same multi-choice question
        a1.selected_choices.set([q1_choices[0], q1_choices[1]])
        a2 = Answer.objects.create(
            requirement_assessment=ra, question=q2, folder=folder
        )
        a2.selected_choices.set([q2_choices[0]])

        ra.compute_score_and_result()
        ra.refresh_from_db()
        assert ra.result == "partially_compliant"

    def test_legacy_true_false_literals_still_work(self, db):
        """Existing YAML libraries using 'true'/'false' keep producing the prior result."""
        folder = Folder.get_root_folder()
        ra, q1, q1_choices, q2, q2_choices = self._build_two_question_ra(
            folder,
            q1_choices=[
                {"ref_id": "A", "value": "Yes", "compute_result": "true"},
                {"ref_id": "B", "value": "No", "compute_result": "false"},
            ],
            q2_choices=[
                {"ref_id": "C", "value": "Yes", "compute_result": "true"},
                {"ref_id": "D", "value": "No", "compute_result": "false"},
            ],
        )

        # Both 'false' -> non_compliant (was non_compliant before the fix too)
        a1 = Answer.objects.create(
            requirement_assessment=ra, question=q1, folder=folder
        )
        a1.selected_choices.set([q1_choices[1]])
        a2 = Answer.objects.create(
            requirement_assessment=ra, question=q2, folder=folder
        )
        a2.selected_choices.set([q2_choices[1]])
        ra.compute_score_and_result()
        ra.refresh_from_db()
        assert ra.result == "non_compliant"

        # Both 'true' -> compliant
        a1.selected_choices.set([q1_choices[0]])
        a2.selected_choices.set([q2_choices[0]])
        ra.compute_score_and_result()
        ra.refresh_from_db()
        assert ra.result == "compliant"

        # Mixed -> partially_compliant
        a1.selected_choices.set([q1_choices[0]])
        a2.selected_choices.set([q2_choices[1]])
        ra.compute_score_and_result()
        ra.refresh_from_db()
        assert ra.result == "partially_compliant"

    def test_mixed_legacy_and_semantic_values(self, db):
        """A framework that mixes legacy 'true' and semantic 'non_compliant' aggregates correctly."""
        folder = Folder.get_root_folder()
        ra, q1, q1_choices, q2, q2_choices = self._build_two_question_ra(
            folder,
            q1_choices=[
                {"ref_id": "A", "value": "Yes", "compute_result": "true"},
            ],
            q2_choices=[
                {
                    "ref_id": "B",
                    "value": "Non-compliant",
                    "compute_result": "non_compliant",
                },
            ],
        )
        a1 = Answer.objects.create(
            requirement_assessment=ra, question=q1, folder=folder
        )
        a1.selected_choices.set([q1_choices[0]])
        a2 = Answer.objects.create(
            requirement_assessment=ra, question=q2, folder=folder
        )
        a2.selected_choices.set([q2_choices[0]])

        ra.compute_score_and_result()
        ra.refresh_from_db()
        assert ra.result == "partially_compliant"


@pytest.mark.django_db
class TestResolveComputeResult:
    """Unit tests for the resolver/aggregator helpers themselves."""

    def test_resolve_known_values(self):
        from core.utils import resolve_compute_result

        assert resolve_compute_result("compliant") == "compliant"
        assert resolve_compute_result("non_compliant") == "non_compliant"
        assert resolve_compute_result("partially_compliant") == "partially_compliant"
        assert resolve_compute_result("not_applicable") == "not_applicable"

    def test_resolve_legacy_booleans(self):
        from core.utils import resolve_compute_result

        assert resolve_compute_result("true") == "compliant"
        assert resolve_compute_result("1") == "compliant"
        assert resolve_compute_result("false") == "non_compliant"
        assert resolve_compute_result("0") == "non_compliant"

    def test_resolve_case_insensitive_and_whitespace(self):
        from core.utils import resolve_compute_result

        assert resolve_compute_result("  Compliant  ") == "compliant"
        assert resolve_compute_result("NON_COMPLIANT") == "non_compliant"

    def test_resolve_empty_and_none(self):
        from core.utils import resolve_compute_result

        assert resolve_compute_result(None) is None
        assert resolve_compute_result("") is None
        assert resolve_compute_result("   ") is None

    def test_resolve_unknown_value_returns_none(self):
        """Unrecognized strings return None instead of contributing."""
        from core.utils import resolve_compute_result

        assert resolve_compute_result("complient") is None  # typo
        assert resolve_compute_result("yes") is None
        assert resolve_compute_result("custom_value") is None

    def test_aggregate_worst_wins(self):
        from core.utils import aggregate_compute_results

        assert aggregate_compute_results([]) is None
        assert aggregate_compute_results([None, None]) is None
        assert aggregate_compute_results(["compliant", "compliant"]) == "compliant"
        assert (
            aggregate_compute_results(["non_compliant", "non_compliant"])
            == "non_compliant"
        )
        assert (
            aggregate_compute_results(["compliant", "non_compliant"])
            == "partially_compliant"
        )
        assert (
            aggregate_compute_results(["partially_compliant"]) == "partially_compliant"
        )
        assert (
            aggregate_compute_results(["not_applicable", "not_applicable"])
            == "not_applicable"
        )
        # NA is neutral: dropped from the pool, other contributions decide.
        assert (
            aggregate_compute_results(["not_applicable", "non_compliant"])
            == "non_compliant"
        )
        assert aggregate_compute_results(["not_applicable", "compliant"]) == "compliant"
        assert (
            aggregate_compute_results(["not_applicable", "partially_compliant"])
            == "partially_compliant"
        )


@pytest.mark.django_db
class TestVisibilityEdgeCases:
    def _make_visibility_setup(self, folder, q1_type, q2_depends_on):
        """Helper to create framework with Q1->Q2 depends_on chain."""
        fw = Framework.objects.create(
            name=f"Vis FW {q2_depends_on}",
            folder=folder,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn=f"urn:test:vis:{id(q2_depends_on)}:req:001",
            ref_id="VIS-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q1_urn = "urn:test:vq1"
        if q2_depends_on and q2_depends_on.get("question") == "VQ1":
            q2_depends_on["question"] = q1_urn
        q1 = Question.objects.create(
            requirement_node=rn,
            urn=q1_urn,
            ref_id="VQ1",
            type=q1_type,
            order=0,
            folder=folder,
            is_published=True,
        )
        q2 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:vq2",
            ref_id="VQ2",
            type=Question.Type.UNIQUE_CHOICE,
            depends_on=q2_depends_on,
            order=1,
            folder=folder,
            is_published=True,
        )
        return fw, rn, q1, q2

    def test_depends_on_condition_all_with_multiple_choice(self, db):
        """Q1 multi-choice answered ["A","B"], Q2 depends_on condition=all answers=["A","B"] -> visible."""
        folder = Folder.get_root_folder()
        fw, rn, q1, q2 = self._make_visibility_setup(
            folder,
            Question.Type.MULTIPLE_CHOICE,
            {
                "question": "VQ1",
                "answers": ["urn:test:choice:vq1:va", "urn:test:choice:vq1:vb"],
                "condition": "all",
            },
        )
        c_a = QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:choice:vq1:va",
            ref_id="VA",
            value="A",
            add_score=5,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        c_b = QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:choice:vq1:vb",
            ref_id="VB",
            value="B",
            add_score=5,
            compute_result="true",
            order=1,
            folder=folder,
            is_published=True,
        )
        # Q2 choices
        q2_c = QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:choice:vq2:vq2a",
            ref_id="VQ2A",
            value="X",
            add_score=1,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:choice:vq2:vq2b",
            ref_id="VQ2B",
            value="Y",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Vis Perim All", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Vis CA All",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        # Answer Q1 with both ["VA","VB"] - Q2 should be visible
        a1 = Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            folder=folder,
        )
        a1.selected_choices.set([c_a, c_b])

        a2 = Answer.objects.create(
            requirement_assessment=ra,
            question=q2,
            folder=folder,
        )
        a2.selected_choices.set([q2_c])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        # Both Q1 and Q2 visible and answered -> result from both
        assert ra.result == "compliant"

    def test_depends_on_condition_all_partial_answer_hides(self, db):
        """Q1 multi-choice answered ["A"] only, Q2 depends_on condition=all answers=["A","B"] -> hidden."""
        folder = Folder.get_root_folder()
        fw, rn, q1, q2 = self._make_visibility_setup(
            folder,
            Question.Type.MULTIPLE_CHOICE,
            {
                "question": "VQ1",
                "answers": ["urn:test:choice:vq1:va2", "urn:test:choice:vq1:vb2"],
                "condition": "all",
            },
        )
        c_a = QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:choice:vq1:va2",
            ref_id="VA2",
            value="A",
            add_score=5,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:choice:vq1:vb2",
            ref_id="VB2",
            value="B",
            add_score=5,
            compute_result="true",
            order=1,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:choice:vq2:vq2c",
            ref_id="VQ2C",
            value="X",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:choice:vq2:vq2d",
            ref_id="VQ2D",
            value="Y",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Vis Perim All2", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Vis CA All2",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        # Answer Q1 with only ["urn:test:choice:vq1:va2"] - Q2 should be hidden (condition=all needs both)
        a1 = Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            folder=folder,
        )
        a1.selected_choices.set([c_a])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        # Only Q1 visible and answered -> compliant
        assert ra.result == "compliant"

    def test_depends_on_condition_all_with_single_choice(self, db):
        """Single-choice 'A', depends_on condition=all answers=['A'] -> visible."""
        folder = Folder.get_root_folder()
        fw, rn, q1, q2 = self._make_visibility_setup(
            folder,
            Question.Type.UNIQUE_CHOICE,
            {
                "question": "VQ1",
                "answers": ["urn:test:choice:vq1:vsa"],
                "condition": "all",
            },
        )
        c_a = QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:choice:vq1:vsa",
            ref_id="VSA",
            value="A",
            add_score=5,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:choice:vq1:vsb",
            ref_id="VSB",
            value="B",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )
        q2_c = QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:choice:vq2:vsq2a",
            ref_id="VSQ2A",
            value="X",
            add_score=1,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:choice:vq2:vsq2b",
            ref_id="VSQ2B",
            value="Y",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Vis Perim SC", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Vis CA SC",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        a1 = Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            folder=folder,
        )
        a1.selected_choices.set([c_a])

        a2 = Answer.objects.create(
            requirement_assessment=ra,
            question=q2,
            folder=folder,
        )
        a2.selected_choices.set([q2_c])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        assert ra.result == "compliant"

    def test_chained_depends_on(self, db):
        """Q1->Q2->Q3 chain. Q3 visible only if Q2 is answered."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Max Agg Framework",
            folder=folder,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:chain:req:001",
            ref_id="CH-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q1 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:chq1",
            ref_id="CHQ1",
            type=Question.Type.UNIQUE_CHOICE,
            order=0,
            folder=folder,
            is_published=True,
        )
        q1_c = QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:choice:chq1:chc1a",
            ref_id="CHC1A",
            value="Yes",
            add_score=1,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:choice:chq1:chc1b",
            ref_id="CHC1B",
            value="No",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )

        q2 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:chq2",
            ref_id="CHQ2",
            type=Question.Type.UNIQUE_CHOICE,
            order=1,
            depends_on={
                "question": "urn:test:chq1",
                "answers": ["urn:test:choice:chq1:chc1a"],
                "condition": "any",
            },
            folder=folder,
            is_published=True,
        )
        q2_c = QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:choice:chq2:chc2a",
            ref_id="CHC2A",
            value="Sub-Yes",
            add_score=1,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:choice:chq2:chc2b",
            ref_id="CHC2B",
            value="Sub-No",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )

        q3 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:chq3",
            ref_id="CHQ3",
            type=Question.Type.UNIQUE_CHOICE,
            order=2,
            depends_on={
                "question": "urn:test:chq2",
                "answers": ["urn:test:choice:chq2:chc2a"],
                "condition": "any",
            },
            folder=folder,
            is_published=True,
        )
        q3_c = QuestionChoice.objects.create(
            question=q3,
            urn="urn:test:choice:chq3:chc3a",
            ref_id="CHC3A",
            value="Deep-Yes",
            add_score=1,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q3,
            urn="urn:test:choice:chq3:chc3b",
            ref_id="CHC3B",
            value="Deep-No",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Chain Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Chain CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        # Answer all three in chain
        a1 = Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            folder=folder,
        )
        a1.selected_choices.set([q1_c])
        a2 = Answer.objects.create(
            requirement_assessment=ra,
            question=q2,
            folder=folder,
        )
        a2.selected_choices.set([q2_c])
        a3 = Answer.objects.create(
            requirement_assessment=ra,
            question=q3,
            folder=folder,
        )
        a3.selected_choices.set([q3_c])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        # All 3 visible and answered -> compliant
        assert ra.result == "compliant"

    def test_depends_on_with_unanswered_dependency(self, db):
        """Q2 depends on Q1, Q1 not answered -> Q2 hidden."""
        folder = Folder.get_root_folder()
        fw, rn, q1, q2 = self._make_visibility_setup(
            folder,
            Question.Type.UNIQUE_CHOICE,
            {
                "question": "urn:test:vq1",
                "answers": ["urn:test:choice:vq1:vua"],
                "condition": "any",
            },
        )
        QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:choice:vq1:vua",
            ref_id="VUA",
            value="A",
            add_score=5,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:choice:vq1:vub",
            ref_id="VUB",
            value="B",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:choice:vq2:vuq2a",
            ref_id="VUQ2A",
            value="X",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:choice:vq2:vuq2b",
            ref_id="VUQ2B",
            value="Y",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Vis Perim UA", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Vis CA UA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        # Don't answer Q1 at all -> Q2 hidden, only Q1 is visible but unanswered
        ra.compute_score_and_result()
        ra.refresh_from_db()

        # Q1 visible but unanswered -> not_assessed
        assert ra.result == "not_assessed"

    def test_depends_on_with_empty_answers_list(self, db):
        """depends_on.answers=[] -> always hidden."""
        folder = Folder.get_root_folder()
        fw, rn, q1, q2 = self._make_visibility_setup(
            folder,
            Question.Type.UNIQUE_CHOICE,
            {"question": "urn:test:vq1", "answers": [], "condition": "any"},
        )
        c_a = QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:choice:vq1:vea",
            ref_id="VEA",
            value="A",
            add_score=5,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:choice:vq1:veb",
            ref_id="VEB",
            value="B",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:choice:vq2:veq2a",
            ref_id="VEQ2A",
            value="X",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:choice:vq2:veq2b",
            ref_id="VEQ2B",
            value="Y",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Vis Perim Empty", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Vis CA Empty",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        # Answer Q1 -> Q2 still hidden because answers=[]
        a1 = Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            folder=folder,
        )
        a1.selected_choices.set([c_a])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        # Only Q1 visible and answered -> compliant (from Q1's result)
        assert ra.result == "compliant"

    def test_depends_on_with_unknown_condition(self, db):
        """condition='foo' -> fallback returns False (hidden)."""
        folder = Folder.get_root_folder()
        fw, rn, q1, q2 = self._make_visibility_setup(
            folder,
            Question.Type.UNIQUE_CHOICE,
            {
                "question": "urn:test:vq1",
                "answers": ["urn:test:choice:vq1:vfa"],
                "condition": "foo",
            },
        )
        c_a = QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:choice:vq1:vfa",
            ref_id="VFA",
            value="A",
            add_score=5,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:choice:vq1:vfb",
            ref_id="VFB",
            value="B",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )
        q2_c = QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:choice:vq2:vfq2a",
            ref_id="VFQ2A",
            value="X",
            add_score=1,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:choice:vq2:vfq2b",
            ref_id="VFQ2B",
            value="Y",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Vis Perim Foo", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Vis CA Foo",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        # Answer Q1 -> Q2 stays hidden (unknown condition falls through to False).
        # Q2's answer is preserved in case the user fixes the condition later.
        a1 = Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            folder=folder,
        )
        a1.selected_choices.set([c_a])
        a2 = Answer.objects.create(
            requirement_assessment=ra,
            question=q2,
            folder=folder,
        )
        a2.selected_choices.set([q2_c])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        # Only Q1 visible and answered with a 'compliant' choice -> compliant
        assert ra.result == "compliant"
