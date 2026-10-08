"""Quick form score aggregation: page aggregation (`sum | max | mean`),
`pages[id].score`, `response.score`, and form-level page modes.

The acceptance case is the original "Supplier risk framework" workbook: per
category the highest rung answered Yes (Excel `MAX`), the tier from the
average of the five category scores (`AVERAGE`, thresholds 1.5 / 2.5 / 3.5),
and "critical data" (row 13) as a knock-out to Critical.
"""

import itertools
import random

import pytest
from rest_framework.test import APIClient

from core.apps import startup
from core.cel_service import (
    evaluate_quick_form,
    evaluate_quick_form_document,
    validate_quick_form_expressions,
)
from core.models import Question, QuickForm, QuickFormResponse, StoredLibrary
from core.quick_form_scoring import aggregate_form, aggregate_page, clamp
from core.utils import apply_answers_dict
from iam.models import Folder
from library.quick_form_editor import (
    editor_doc_to_quick_form_object,
    quick_form_to_editor_doc,
)

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _item(score, max_score=4, weight=1, answered=True):
    return {
        "score": score,
        "max_score": max_score,
        "weight": weight,
        "answered": answered,
    }


class TestAggregatePage:
    def test_page_without_scorable_questions_has_no_score(self):
        assert aggregate_page([], "max") is None

    @pytest.mark.parametrize(
        "aggregation,expected",
        [("sum", (5.0, 12.0)), ("max", (3.0, 4.0)), ("mean", (2.5, 4.0))],
    )
    def test_answered_questions(self, aggregation, expected):
        items = [_item(2), _item(3), _item(0, answered=False)]
        result = aggregate_page(items, aggregation)
        assert (result["score"], result["score_max"]) == expected

    def test_unanswered_page_scores_zero(self):
        result = aggregate_page([_item(0, answered=False)], "max")
        assert result["score"] == 0.0

    def test_mean_is_weighted(self):
        # Scores already carry the weight: 2*3 and 1*1 over a weight of 4.
        items = [_item(6, max_score=12, weight=3), _item(1)]
        assert aggregate_page(items, "mean")["score"] == 1.75

    def test_unknown_aggregation_falls_back_to_sum(self):
        assert aggregate_page([_item(2), _item(3)], "median")["score"] == 5.0

    def test_results_are_floats(self):
        # CEL compares a double with an int literal, not an int with a double.
        result = aggregate_page([_item(2)], "sum")
        assert isinstance(result["score"], float)
        assert isinstance(result["score_max"], float)


class TestAggregateForm:
    pages = [{"score": 1.0, "score_max": 4.0}, {"score": 4.0, "score_max": 4.0}]

    def test_pages_sum_and_mean(self):
        assert aggregate_form([], self.pages, "pages_sum") == 5.0
        assert aggregate_form([], self.pages, "pages_mean") == 2.5

    def test_page_modes_need_a_scored_page(self):
        assert aggregate_form([], [], "pages_mean") is None

    def test_question_modes_are_unchanged(self):
        items = [_item(2), _item(4), _item(3, answered=False)]
        assert aggregate_form(items, self.pages, "sum") == 6.0
        assert aggregate_form(items, self.pages, "mean") == 3.0
        assert aggregate_form([_item(0, answered=False)], [], "sum") is None

    def test_clamp(self):
        assert clamp(7.5, (0, 5)) == 5.0
        assert clamp(None, (0, 5)) is None


# ---------------------------------------------------------------------------
# The Excel workbook, rebuilt with page aggregation
# ---------------------------------------------------------------------------

CATEGORIES = [
    "data_access",
    "network_access",
    "compliance_level",
    "business_impact",
    "potential_equivalent_loss",
]
BASE = "urn:test:risk:qf_page:supplier-tiering"


def _question_urn(category, rung):
    return f"{BASE}:{category}:question:q{rung}"


def _yes(category, rung):
    return f"{_question_urn(category, rung)}:choice:yes"


def _no(category, rung):
    return f"{_question_urn(category, rung)}:choice:no"


KNOCKOUT = '"data_access:question:q4:choice:yes" in answers["data_access:question:q4"].selected_choices'

TIERING_FORM = {
    "urn": "urn:test:risk:quick_form:supplier-tiering",
    "ref_id": "supplier-tiering",
    "name": "Supplier tiering",
    "scores_definition": {"min": 0, "max": 4, "aggregation": "pages_mean"},
    "outcomes_definition": [
        {
            "ref_id": "critical",
            "expression": f"{KNOCKOUT} || response.score > 3.5",
        },
        {
            "ref_id": "high",
            "expression": f"!({KNOCKOUT}) && response.score > 2.5 && response.score <= 3.5",
        },
        {
            "ref_id": "medium",
            "expression": f"!({KNOCKOUT}) && response.score > 1.5 && response.score <= 2.5",
        },
        {
            "ref_id": "low",
            "expression": f"!({KNOCKOUT}) && response.score <= 1.5",
        },
    ],
    "pages": [
        {
            "urn": f"{BASE}:{category}",
            "ref_id": category,
            "name": category,
            "aggregation": "max",
            "questions": {
                _question_urn(category, rung): {
                    "type": "unique_choice",
                    "text": f"{category} rung {rung}",
                    "choices": [
                        {
                            "urn": _yes(category, rung),
                            "value": "Yes",
                            "add_score": rung,
                        },
                        {"urn": _no(category, rung), "value": "No", "add_score": 0},
                    ],
                }
                for rung in range(1, 5)
            },
        }
        for category in CATEGORIES
    ],
}


def _excel_tier(yes_rungs: dict[str, set[int]]) -> str:
    """The workbook's own formulas, cell for cell."""
    category_scores = [max(yes_rungs[c], default=0) for c in CATEGORIES]  # E10..E26
    average = sum(category_scores) / len(category_scores)  # E31
    if 4 in yes_rungs["data_access"]:  # C13 = "Yes"
        return "critical"
    if average <= 1.5:
        return "low"
    if average <= 2.5:
        return "medium"
    if average <= 3.5:
        return "high"
    return "critical"


def _answers(yes_rungs: dict[str, set[int]]) -> dict:
    return {
        _question_urn(category, rung): (
            _yes(category, rung) if rung in yes_rungs[category] else _no(category, rung)
        )
        for category in CATEGORIES
        for rung in range(1, 5)
    }


def _scenarios():
    """Every combination of category scores 0-4 (5^5), plus a fixed random
    sample of arbitrary Yes/No grids, where lower rungs are also Yes."""
    for levels in itertools.product(range(5), repeat=len(CATEGORIES)):
        yield {c: ({level} if level else set()) for c, level in zip(CATEGORIES, levels)}
    rng = random.Random(4936)
    for _ in range(300):
        yield {
            c: {rung for rung in range(1, 5) if rng.random() < 0.4} for c in CATEGORIES
        }


class TestSupplierTieringWorkbook:
    def test_form_expressions_are_valid(self):
        assert validate_quick_form_expressions(TIERING_FORM) == []

    def test_every_scenario_matches_the_workbook(self):
        mismatches = []
        count = 0
        for yes_rungs in _scenarios():
            count += 1
            result = evaluate_quick_form_document(TIERING_FORM, _answers(yes_rungs))
            fired = set(result["computed_outcome"])
            expected = _excel_tier(yes_rungs)
            if fired != {expected}:
                mismatches.append((yes_rungs, expected, sorted(fired)))
        assert count == 5**5 + 300
        assert not mismatches, f"{len(mismatches)} mismatches, first: {mismatches[:3]}"

    def test_scores_are_exposed_unrounded(self):
        yes_rungs = {c: set() for c in CATEGORIES}
        yes_rungs["data_access"] = {1, 3}
        yes_rungs["business_impact"] = {2}
        context = evaluate_quick_form_document(TIERING_FORM, _answers(yes_rungs))[
            "context"
        ]
        assert context["pages"]["data_access"]["score"] == 3.0
        assert context["pages"]["data_access"]["score_max"] == 4.0
        assert context["pages"]["business_impact"]["score"] == 2.0
        assert context["response"]["score"] == 1.0  # (3 + 2) / 5


# ---------------------------------------------------------------------------
# Expression checks
# ---------------------------------------------------------------------------


class TestExpressionValidation:
    def test_page_and_response_scores_are_known_roots(self):
        form = {
            **TIERING_FORM,
            "outcomes_definition": [
                {"ref_id": "a", "expression": 'pages["data_access"].score >= 3'},
                {"ref_id": "b", "expression": "response.score > 2.5"},
                {"ref_id": "c", "expression": 'pages["data_access"].score_max > 0'},
            ],
        }
        assert validate_quick_form_expressions(form) == []

    def test_int_equality_against_a_double_score_is_caught_at_save(self):
        # Scores are doubles; `== 3` has no int/double overload in CEL. The
        # builder refuses the save instead of the rule silently never firing.
        form = {
            **TIERING_FORM,
            "outcomes_definition": [
                {"ref_id": "a", "expression": 'pages["data_access"].score == 3'}
            ],
        }
        errors = validate_quick_form_expressions(form)
        assert [e["ref_id"] for e in errors] == ["a"]


# ---------------------------------------------------------------------------
# Builder round trip
# ---------------------------------------------------------------------------


class TestBuilderRoundTrip:
    def _round_trip(self, mutate=None):
        doc = quick_form_to_editor_doc(TIERING_FORM)
        if mutate:
            mutate(doc)
        return editor_doc_to_quick_form_object(doc, existing=TIERING_FORM)

    def test_page_aggregation_survives_a_save(self):
        result = self._round_trip()
        assert [p.get("aggregation") for p in result["pages"]] == ["max"] * 5
        assert result["scores_definition"]["aggregation"] == "pages_mean"

    def test_editor_can_change_it(self):
        def set_mean(doc):
            doc["nodes"][0]["aggregation"] = "mean"
            doc["nodes"][1]["aggregation"] = "sum"

        pages = self._round_trip(set_mean)["pages"]
        assert pages[0]["aggregation"] == "mean"
        # The default is not written out.
        assert "aggregation" not in pages[1]

    def test_absent_key_keeps_the_document_value(self):
        def drop(doc):
            for node in doc["nodes"]:
                node.pop("aggregation", None)

        pages = self._round_trip(drop)["pages"]
        assert pages[0]["aggregation"] == "max"

    def test_unknown_value_is_refused(self):
        from library.builder import BuilderError

        def bad(doc):
            doc["nodes"][0]["aggregation"] = "median"

        with pytest.raises(BuilderError):
            self._round_trip(bad)


# ---------------------------------------------------------------------------
# Library load, live evaluation and preview parity
# ---------------------------------------------------------------------------

LIBRARY_YAML = """
urn: urn:test:risk:library:page-aggregation
locale: en
ref_id: page-aggregation
name: Page aggregation
description: test
copyright: test
version: 1
provider: test
packager: test
objects:
  quick_forms:
    - urn: urn:test:risk:quick_form:page-aggregation
      ref_id: page-aggregation
      name: Page aggregation
      scores_definition:
        min: 0
        max: 4
        aggregation: pages_mean
      outcomes_definition:
        - ref_id: above_two
          expression: 'response.score > 2 && pages["cat_a"].score == 3.0'
      pages:
        - urn: urn:test:risk:qf_page:page-aggregation:cat_a
          ref_id: cat_a
          name: Category A
          aggregation: max
          questions:
            urn:test:risk:qf_page:page-aggregation:cat_a:question:q1:
              type: unique_choice
              text: First
              choices:
                - urn: urn:test:risk:qf_page:page-aggregation:cat_a:question:q1:choice:yes
                  value: Yes
                  add_score: 1
                - urn: urn:test:risk:qf_page:page-aggregation:cat_a:question:q1:choice:no
                  value: No
                  add_score: 0
            urn:test:risk:qf_page:page-aggregation:cat_a:question:q3:
              type: unique_choice
              text: Third
              choices:
                - urn: urn:test:risk:qf_page:page-aggregation:cat_a:question:q3:choice:yes
                  value: Yes
                  add_score: 3
                - urn: urn:test:risk:qf_page:page-aggregation:cat_a:question:q3:choice:no
                  value: No
                  add_score: 0
        - urn: urn:test:risk:qf_page:page-aggregation:cat_b
          ref_id: cat_b
          name: Category B
          aggregation: max
          questions:
            urn:test:risk:qf_page:page-aggregation:cat_b:question:q2:
              type: unique_choice
              text: Second
              choices:
                - urn: urn:test:risk:qf_page:page-aggregation:cat_b:question:q2:choice:yes
                  value: Yes
                  add_score: 2
                - urn: urn:test:risk:qf_page:page-aggregation:cat_b:question:q2:choice:no
                  value: No
                  add_score: 0
"""
Q = "urn:test:risk:qf_page:page-aggregation"
ANSWERS = {
    f"{Q}:cat_a:question:q1": f"{Q}:cat_a:question:q1:choice:yes",
    f"{Q}:cat_a:question:q3": f"{Q}:cat_a:question:q3:choice:yes",
    f"{Q}:cat_b:question:q2": f"{Q}:cat_b:question:q2:choice:no",
}


@pytest.fixture
def loaded_form():
    startup(sender=None, **{})
    stored, error = StoredLibrary.store_library_content(LIBRARY_YAML.encode("utf-8"))
    assert error is None, error
    assert stored.load() is None
    return QuickForm.objects.get(urn="urn:test:risk:quick_form:page-aggregation")


@pytest.mark.django_db
class TestLiveEvaluation:
    def _response(self, form, answers):
        folder = Folder.objects.create(
            name="qf-agg", parent_folder=Folder.get_root_folder()
        )
        response = QuickFormResponse.objects.create(
            name="scored", quick_form=form, folder=folder
        )
        questions = {q.urn: q for q in Question.objects.filter(page__quick_form=form)}
        apply_answers_dict("response", response, questions, answers)
        return response

    def test_library_load_stores_page_aggregation(self, loaded_form):
        assert list(
            loaded_form.pages.order_by("order").values_list("aggregation", flat=True)
        ) == ["max", "max"]

    def test_live_context_score_and_outcome(self, loaded_form):
        response = self._response(loaded_form, ANSWERS)
        result = evaluate_quick_form(response, persist=True)
        context = result["context"]
        # max(1, 3) = 3 on A, 0 on B, mean 1.5.
        assert context["pages"]["cat_a"]["score"] == 3.0
        assert context["pages"]["cat_b"]["score"] == 0.0
        assert context["response"]["score"] == 1.5
        assert result["computed_outcome"] == {}
        response.refresh_from_db()
        assert response.score == 1.5

    def test_outcome_fires_on_the_unrounded_score(self, loaded_form):
        answers = {
            **ANSWERS,
            f"{Q}:cat_b:question:q2": f"{Q}:cat_b:question:q2:choice:yes",
        }
        result = evaluate_quick_form(self._response(loaded_form, answers))
        assert result["context"]["response"]["score"] == 2.5
        assert set(result["computed_outcome"]) == {"above_two"}

    def test_published_preview_matches_live(self, loaded_form):
        from core.models import User
        from iam.models import UserGroup
        from knox.models import AuthToken

        user = User.objects.create_user(email="qf-agg@test.local", is_published=True)
        admin_group = UserGroup.objects.get(name="BI-UG-ADM")
        user.folder = admin_group.folder
        user.save()
        admin_group.user_set.add(user)
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
        )

        answers = {
            **ANSWERS,
            f"{Q}:cat_b:question:q2": f"{Q}:cat_b:question:q2:choice:yes",
        }
        preview = client.post(
            f"/api/quick-forms/{loaded_form.id}/preview/",
            {"answers": answers},
            format="json",
        )
        assert preview.status_code == 200, preview.json()
        live = evaluate_quick_form(self._response(loaded_form, answers), persist=False)
        assert preview.json()["score"] == live["score"] == 2.5
        assert set(preview.json()["computed_outcome"]) == set(live["computed_outcome"])

    def test_invalid_page_aggregation_is_refused_at_load(self):
        startup(sender=None, **{})
        bad = LIBRARY_YAML.replace("page-aggregation", "page-aggregation-bad").replace(
            "aggregation: max", "aggregation: median", 1
        )
        stored, error = StoredLibrary.store_library_content(bad.encode("utf-8"))
        assert error is None, error
        assert stored.load() is not None
