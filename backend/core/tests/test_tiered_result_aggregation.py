"""Tests for `tiered_all` result aggregation.

Worst-wins aggregation collapses any mix of compliant and non_compliant to
partially_compliant, which cannot express "all of these statements must hold".
`tiered_all` can: a tier is earned only when every statement stating it holds.

The reference case is the NCSC CAF, whose indicator tables print the rule:

    Not Achieved       at least one of the following statements is true
    Partially Achieved all the following statements are true
    Achieved           all the following statements are true
"""

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
from core.utils import aggregate_tiered_results, resolve_result_tier
from iam.models import Folder

# (tier stated by the True choice, result of the False choice)
ACHIEVED = ("compliant", "non_compliant")
PARTIAL = ("partially_compliant", None)
BLOCKING = ("non_compliant", None)


class TestResolveResultTier:
    @pytest.mark.parametrize(
        ("compute_results", "expected"),
        [
            (["compliant", "non_compliant"], "compliant"),
            (["partially_compliant", None], "partially_compliant"),
            (["non_compliant", None], "blocking"),
            ([None, None], None),
            ([], None),
            # A choice that can set the top tier wins over the rest.
            (["non_compliant", "partially_compliant", "compliant"], "compliant"),
            # Unparseable values are ignored, like everywhere else.
            (["nonsense"], None),
            (["not_applicable"], None),
        ],
    )
    def test_tier_is_read_from_the_choices(self, compute_results, expected):
        assert resolve_result_tier(compute_results) == expected


class TestAggregateTieredResults:
    def test_all_achieved_statements_true_is_compliant(self):
        answers = [("compliant", ["compliant"])] * 3
        assert aggregate_tiered_results(answers) == "compliant"

    def test_one_achieved_statement_false_drops_the_tier(self):
        answers = [
            ("compliant", ["compliant"]),
            ("compliant", ["compliant"]),
            ("compliant", ["non_compliant"]),
        ]
        # Worst-wins would call this partially compliant; the CAF calls it
        # Not achieved when there is no Partially achieved level to fall to.
        assert aggregate_tiered_results(answers) == "non_compliant"

    def test_falls_back_to_the_partial_tier(self):
        answers = [
            ("compliant", ["non_compliant"]),
            ("partially_compliant", ["partially_compliant"]),
            ("partially_compliant", ["partially_compliant"]),
        ]
        assert aggregate_tiered_results(answers) == "partially_compliant"

    def test_partial_tier_must_hold_in_full_too(self):
        answers = [
            ("compliant", ["compliant"]),
            ("compliant", ["non_compliant"]),
            ("partially_compliant", ["partially_compliant"]),
            ("partially_compliant", ["non_compliant"]),
        ]
        assert aggregate_tiered_results(answers) == "non_compliant"

    def test_a_blocking_statement_denies_every_tier(self):
        answers = [
            ("blocking", ["non_compliant"]),
            ("compliant", ["compliant"]),
            ("compliant", ["compliant"]),
        ]
        assert aggregate_tiered_results(answers) == "non_compliant"

    def test_an_untriggered_blocking_statement_is_silent(self):
        answers = [
            ("blocking", []),
            ("compliant", ["compliant"]),
        ]
        assert aggregate_tiered_results(answers) == "compliant"

    def test_not_applicable_answers_are_neutral(self):
        answers = [
            ("compliant", ["compliant"]),
            ("compliant", ["not_applicable"]),
        ]
        assert aggregate_tiered_results(answers) == "compliant"

    def test_everything_not_applicable(self):
        answers = [("compliant", ["not_applicable"])] * 2
        assert aggregate_tiered_results(answers) == "not_applicable"

    def test_questions_stating_no_tier_are_ignored(self):
        assert aggregate_tiered_results([]) is None
        assert aggregate_tiered_results([(None, []), (None, ["compliant"])]) is None

    def test_answering_without_affirming_the_tier_fails_it(self):
        """The False side of "all the following are true" states nothing, and
        that is exactly what makes the tier fail."""
        assert aggregate_tiered_results([("compliant", [])]) == "non_compliant"
        assert (
            aggregate_tiered_results(
                [("compliant", []), ("partially_compliant", ["partially_compliant"])]
            )
            == "partially_compliant"
        )

    def test_only_untriggered_blocking_statements(self):
        """Nothing states a higher tier and no failure condition fired."""
        assert (
            aggregate_tiered_results([("blocking", []), ("blocking", [])])
            == "compliant"
        )
        assert (
            aggregate_tiered_results([("blocking", ["not_applicable"])])
            == "not_applicable"
        )


@pytest.fixture
def tiered_setup(db):
    """A framework with one tiered outcome carrying NA / PA / A statements."""
    folder = Folder.get_root_folder()

    def build(result_aggregation):
        framework = Framework.objects.create(
            name=f"Tiered FW {result_aggregation}",
            urn=f"urn:test:tiered:fw:{result_aggregation}",
            folder=folder,
            result_aggregation=result_aggregation,
        )
        node = RequirementNode.objects.create(
            framework=framework,
            urn=f"urn:test:tiered:req:{result_aggregation}",
            ref_id="OUTCOME",
            assessable=True,
            folder=folder,
        )

        questions = {}
        for order, (name, (on_true, on_false)) in enumerate(
            [("na", BLOCKING), ("pa", PARTIAL), ("a1", ACHIEVED), ("a2", ACHIEVED)]
        ):
            question = Question.objects.create(
                requirement_node=node,
                urn=f"urn:test:tiered:{result_aggregation}:q:{name}",
                text=name,
                type=Question.Type.UNIQUE_CHOICE,
                order=order,
                folder=folder,
            )
            true_choice = QuestionChoice.objects.create(
                question=question,
                urn=f"{question.urn}:true",
                value="True",
                compute_result=on_true,
                order=0,
                folder=folder,
            )
            false_choice = QuestionChoice.objects.create(
                question=question,
                urn=f"{question.urn}:false",
                value="False",
                compute_result=on_false,
                order=1,
                folder=folder,
            )
            questions[name] = (question, true_choice, false_choice)

        perimeter = Perimeter.objects.create(
            name=f"Tiered perimeter {result_aggregation}", folder=folder
        )
        ca = ComplianceAssessment.objects.create(
            name=f"Tiered CA {result_aggregation}",
            framework=framework,
            folder=folder,
            perimeter=perimeter,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=node, folder=folder
        )
        return {"ra": ra, "questions": questions, "folder": folder}

    return build


def answer(setup, name, value: bool):
    question, true_choice, false_choice = setup["questions"][name]
    row, _ = Answer.objects.get_or_create(
        requirement_assessment=setup["ra"],
        question=question,
        defaults={"folder": setup["folder"]},
    )
    row.selected_choices.set([true_choice if value else false_choice])


@pytest.mark.django_db
class TestTieredAggregationThroughRecompute:
    def test_every_achieved_statement_true(self, tiered_setup):
        setup = tiered_setup(Framework.ResultAggregation.TIERED_ALL)
        answer(setup, "na", False)
        answer(setup, "pa", True)
        answer(setup, "a1", True)
        answer(setup, "a2", True)

        setup["ra"].compute_score_and_result()
        assert setup["ra"].result == RequirementAssessment.Result.COMPLIANT

    def test_partial_when_only_the_lower_tier_holds(self, tiered_setup):
        setup = tiered_setup(Framework.ResultAggregation.TIERED_ALL)
        answer(setup, "na", False)
        answer(setup, "pa", True)
        answer(setup, "a1", True)
        answer(setup, "a2", False)

        setup["ra"].compute_score_and_result()
        assert setup["ra"].result == RequirementAssessment.Result.PARTIALLY_COMPLIANT

    def test_not_achieved_when_neither_tier_holds(self, tiered_setup):
        setup = tiered_setup(Framework.ResultAggregation.TIERED_ALL)
        answer(setup, "na", False)
        answer(setup, "pa", False)
        answer(setup, "a1", True)
        answer(setup, "a2", False)

        setup["ra"].compute_score_and_result()
        assert setup["ra"].result == RequirementAssessment.Result.NON_COMPLIANT

    def test_a_triggered_blocking_statement_overrides_the_rest(self, tiered_setup):
        setup = tiered_setup(Framework.ResultAggregation.TIERED_ALL)
        answer(setup, "na", True)
        answer(setup, "pa", True)
        answer(setup, "a1", True)
        answer(setup, "a2", True)

        setup["ra"].compute_score_and_result()
        assert setup["ra"].result == RequirementAssessment.Result.NON_COMPLIANT

    def test_result_waits_for_a_complete_questionnaire(self, tiered_setup):
        setup = tiered_setup(Framework.ResultAggregation.TIERED_ALL)
        answer(setup, "a1", True)
        answer(setup, "a2", True)

        setup["ra"].compute_score_and_result()
        assert setup["ra"].result == RequirementAssessment.Result.NOT_ASSESSED

    def test_per_answer_is_untouched_and_still_the_default(self, tiered_setup):
        setup = tiered_setup(Framework.ResultAggregation.PER_ANSWER)
        assert (
            Framework.objects.create(
                name="Default FW",
                urn="urn:test:tiered:fw:default",
                folder=Folder.get_root_folder(),
            ).result_aggregation
            == Framework.ResultAggregation.PER_ANSWER
        )

        answer(setup, "na", False)
        answer(setup, "pa", True)
        answer(setup, "a1", True)
        answer(setup, "a2", False)

        setup["ra"].compute_score_and_result()
        # compliant + partially_compliant + non_compliant mixed together.
        assert setup["ra"].result == RequirementAssessment.Result.PARTIALLY_COMPLIANT
