"""Numeric outcome rules (`kind: number`): they compute a value instead of
firing, run before the yes/no rules in definition order, and are read back as
`values.<ref_id>`. Results live in `computed_values`, never in
`computed_outcome`, whose keys read everywhere as classifications that fired.
"""

import copy

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.cel_service import (
    evaluate_quick_form,
    evaluate_quick_form_document,
    validate_quick_form_expressions,
)
from core.models import Question, QuickForm, QuickFormResponse, StoredLibrary, User
from core.tests.test_quick_form_scoring import (
    CATEGORIES,
    KNOCKOUT,
    TIERING_FORM,
    _answers,
    _excel_tier,
    _scenarios,
)
from core.utils import apply_answers_dict
from iam.models import Folder, UserGroup


def _with_rules(rules):
    form = copy.deepcopy(TIERING_FORM)
    form["outcomes_definition"] = rules
    return form


def _none_yes():
    return {c: set() for c in CATEGORIES}


class TestDocumentEvaluation:
    def test_numeric_rule_produces_a_value_and_does_not_fire(self):
        form = _with_rules(
            [{"ref_id": "risk", "kind": "number", "expression": "response.score"}]
        )
        yes = _none_yes()
        yes["data_access"] = {3}
        yes["business_impact"] = {2}
        result = evaluate_quick_form_document(form, _answers(yes))
        assert result["computed_values"] == {"risk": 1.0}
        assert result["computed_outcome"] == {}

    def test_yes_no_rules_read_values(self):
        form = _with_rules(
            [
                {"ref_id": "risk", "kind": "number", "expression": "response.score"},
                {"ref_id": "watch", "expression": "values.risk >= 1.0"},
            ]
        )
        yes = _none_yes()
        yes["data_access"] = {4}
        yes["network_access"] = {1}
        result = evaluate_quick_form_document(form, _answers(yes))
        assert set(result["computed_outcome"]) == {"watch"}

    def test_numeric_rules_chain_in_order(self):
        form = _with_rules(
            [
                {
                    "ref_id": "worst",
                    "kind": "number",
                    "expression": 'pages["data_access"].score',
                },
                {
                    "ref_id": "doubled",
                    "kind": "number",
                    "expression": "values.worst * 2.0",
                },
            ]
        )
        yes = _none_yes()
        yes["data_access"] = {2}
        values = evaluate_quick_form_document(form, _answers(yes))["computed_values"]
        assert values == {"worst": 2.0, "doubled": 4.0}

    def test_int_results_are_stored_as_floats(self):
        form = _with_rules(
            [
                {
                    "ref_id": "count",
                    "kind": "number",
                    "expression": "response.total_count",
                }
            ]
        )
        values = evaluate_quick_form_document(form, _answers(_none_yes()))[
            "computed_values"
        ]
        assert values == {"count": 20.0}
        assert isinstance(values["count"], float)

    @pytest.mark.parametrize(
        "expression",
        ["response.complete", "'high'", "values.missing", "1 / 0"],
        ids=["boolean", "string", "unknown value", "error"],
    )
    def test_a_rule_that_cannot_give_a_number_is_skipped(self, expression):
        form = _with_rules(
            [
                {"ref_id": "bad", "kind": "number", "expression": expression},
                {"ref_id": "ok", "kind": "number", "expression": "response.score"},
            ]
        )
        values = evaluate_quick_form_document(form, _answers(_none_yes()))[
            "computed_values"
        ]
        assert "bad" not in values
        assert values["ok"] == 0.0


class TestWorkbookWithANumericRule:
    """The Excel workbook again, the tier rules now reading one numeric value."""

    FORM = _with_rules(
        [
            {"ref_id": "avg", "kind": "number", "expression": "response.score"},
            {"ref_id": "critical", "expression": f"{KNOCKOUT} || values.avg > 3.5"},
            {
                "ref_id": "high",
                "expression": f"!({KNOCKOUT}) && values.avg > 2.5 && values.avg <= 3.5",
            },
            {
                "ref_id": "medium",
                "expression": f"!({KNOCKOUT}) && values.avg > 1.5 && values.avg <= 2.5",
            },
            {"ref_id": "low", "expression": f"!({KNOCKOUT}) && values.avg <= 1.5"},
        ]
    )

    def test_form_is_valid(self):
        assert validate_quick_form_expressions(self.FORM) == []

    def test_every_scenario_matches_the_workbook(self):
        mismatches = []
        for yes_rungs in _scenarios():
            result = evaluate_quick_form_document(self.FORM, _answers(yes_rungs))
            expected = _excel_tier(yes_rungs)
            if set(result["computed_outcome"]) != {expected}:
                mismatches.append((yes_rungs, expected, result["computed_outcome"]))
            category_scores = [max(yes_rungs[c], default=0) for c in CATEGORIES]
            assert result["computed_values"]["avg"] == pytest.approx(
                sum(category_scores) / len(category_scores)
            )
        assert not mismatches, f"{len(mismatches)} mismatches: {mismatches[:3]}"


class TestValidation:
    def _errors(self, rules, pages=None):
        form = _with_rules(rules)
        if pages is not None:
            form["pages"] = pages
        return {e["ref_id"]: e["error"] for e in validate_quick_form_expressions(form)}

    def test_numeric_rule_must_return_a_number(self):
        errors = self._errors(
            [{"ref_id": "risk", "kind": "number", "expression": "response.complete"}]
        )
        assert "must return a number" in errors["risk"]

    def test_a_numeric_rule_only_sees_the_values_above_it(self):
        errors = self._errors(
            [
                {"ref_id": "a", "kind": "number", "expression": "values.b + 1.0"},
                {"ref_id": "b", "kind": "number", "expression": "response.score"},
            ]
        )
        assert set(errors) == {"a"}
        assert "listed before it" in errors["a"]

    def test_an_unknown_page_or_question_names_the_ones_that_exist(self):
        page = TIERING_FORM["pages"][0]
        page_id = page["urn"].split(":", 5)[5]
        errors = self._errors(
            [
                {"ref_id": "p", "expression": 'pages["nope"].score > 1.0'},
                {"ref_id": "q", "expression": 'answers["nope"].answered'},
            ]
        )
        assert errors["p"].startswith("No page 'nope' in this form. Known: ")
        assert page_id in errors["p"]
        assert errors["q"].startswith("No answer 'nope' in this form. Known: ")

    def test_yes_no_rules_see_every_value(self):
        assert (
            self._errors(
                [
                    {"ref_id": "flag", "expression": "values.risk > 2.0"},
                    {
                        "ref_id": "risk",
                        "kind": "number",
                        "expression": "response.score",
                    },
                ]
            )
            == {}
        )

    def test_unknown_kind_is_refused(self):
        errors = self._errors(
            [{"ref_id": "x", "kind": "text", "expression": "response.complete"}]
        )
        assert "Unknown rule kind" in errors["x"]

    def test_page_visibility_cannot_read_values(self):
        pages = copy.deepcopy(TIERING_FORM["pages"])
        pages[1]["visibility_expression"] = "values.risk > 1.0"
        errors = self._errors(
            [{"ref_id": "risk", "kind": "number", "expression": "response.score"}],
            pages=pages,
        )
        assert set(errors) == {"network_access"}


LIBRARY_YAML = """
urn: urn:test:risk:library:numeric-outcomes
locale: en
ref_id: numeric-outcomes
name: Numeric outcomes
description: test
copyright: test
version: 1
provider: test
packager: test
objects:
  quick_forms:
    - urn: urn:test:risk:quick_form:numeric-outcomes
      ref_id: numeric-outcomes
      name: Numeric outcomes
      scores_definition:
        min: 0
        max: 4
        aggregation: pages_mean
      outcomes_definition:
        - ref_id: risk
          kind: number
          label: Risk score
          expression: response.score
        - ref_id: high
          label: High
          color: '#ea580c'
          expression: values.risk > 2.0
      pages:
        - urn: urn:test:risk:qf_page:numeric-outcomes:a
          ref_id: a
          name: A
          aggregation: max
          questions:
            urn:test:risk:qf_page:numeric-outcomes:a:question:q:
              type: unique_choice
              text: Level
              choices:
                - urn: urn:test:risk:qf_page:numeric-outcomes:a:question:q:choice:one
                  value: One
                  add_score: 1
                - urn: urn:test:risk:qf_page:numeric-outcomes:a:question:q:choice:three
                  value: Three
                  add_score: 3
        - urn: urn:test:risk:qf_page:numeric-outcomes:b
          ref_id: b
          name: B
          aggregation: max
          questions:
            urn:test:risk:qf_page:numeric-outcomes:b:question:q:
              type: unique_choice
              text: Level
              choices:
                - urn: urn:test:risk:qf_page:numeric-outcomes:b:question:q:choice:two
                  value: Two
                  add_score: 2
"""
Q = "urn:test:risk:qf_page:numeric-outcomes"
ANSWERS = {
    f"{Q}:a:question:q": f"{Q}:a:question:q:choice:three",
    f"{Q}:b:question:q": f"{Q}:b:question:q:choice:two",
}


@pytest.fixture
def form():
    startup(sender=None, **{})
    stored, error = StoredLibrary.store_library_content(LIBRARY_YAML.encode("utf-8"))
    assert error is None, error
    assert stored.load() is None
    return QuickForm.objects.get(urn="urn:test:risk:quick_form:numeric-outcomes")


def _admin_client():
    user = User.objects.create_user(email="qf-values@test.local", is_published=True)
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    user.folder = admin_group.folder
    user.save()
    admin_group.user_set.add(user)
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
    )
    return client


@pytest.mark.django_db
class TestLiveValues:
    def _response(self, form):
        folder = Folder.objects.create(
            name="qf-values", parent_folder=Folder.get_root_folder()
        )
        response = QuickFormResponse.objects.create(
            name="valued", quick_form=form, folder=folder
        )
        questions = {q.urn: q for q in Question.objects.filter(page__quick_form=form)}
        apply_answers_dict("response", response, questions, ANSWERS)
        return response

    def test_values_persist_apart_from_outcomes(self, form):
        response = self._response(form)
        evaluate_quick_form(response, persist=True)
        response.refresh_from_db()
        assert response.computed_values == {"risk": 2.5}
        assert set(response.computed_outcome) == {"high"}
        assert response.outcome_refs == "high"
        assert list(response.outcomes.values_list("ref_id", flat=True)) == ["high"]
        # The stored score keeps its decimals now.
        assert response.score == 2.5

    def test_endpoints_return_values(self, form):
        client = _admin_client()
        response = self._response(form)
        preview = client.post(
            f"/api/quick-forms/{form.id}/preview/",
            {"answers": ANSWERS},
            format="json",
        )
        assert preview.status_code == 200, preview.json()
        assert preview.json()["computed_values"] == {"risk": 2.5}

        evaluate_quick_form(response, persist=True)
        detail = client.get(f"/api/quick-form-responses/{response.id}/")
        assert detail.status_code == 200, detail.json()
        assert detail.json()["computed_values"] == {"risk": 2.5}

    def test_values_cannot_be_written_through_the_api(self, form):
        client = _admin_client()
        response = self._response(form)
        client.patch(
            f"/api/quick-form-responses/{response.id}/",
            {"computed_values": {"risk": 99}},
            format="json",
        )
        response.refresh_from_db()
        assert response.computed_values != {"risk": 99}
