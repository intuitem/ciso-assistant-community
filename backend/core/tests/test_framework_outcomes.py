"""Framework outcome rules: ordered evaluation, number rules, rules limited to
implementation groups, and the audit's scores in the CEL context."""

import json
from pathlib import Path

import pytest
from django.db import transaction

from core.cel_service import (
    _add_scores,
    build_cel_context,
    evaluate_outcomes,
    validate_framework_expressions,
)
from core.models import (
    ComplianceAssessment,
    Framework,
    LoadedLibrary,
    RequirementAssessment,
    RequirementNode,
    StoredLibrary,
)
from iam.models import Folder

FIELDS = (
    Path(__file__).resolve().parents[3]
    / "frontend/src/lib/components/FrameworkBuilder/cel-fields.json"
)
CYFUN = Path(__file__).resolve().parents[2] / "library/libraries/cyfun2025.yaml"
NS = "urn:test:risk:req_node:levels"


@pytest.fixture
def levels(db, django_capture_on_commit_callbacks):
    folder = Folder.get_root_folder()
    framework = Framework.objects.create(
        name="Levels",
        urn="urn:test:framework:levels",
        folder=folder,
        min_score=1,
        max_score=5,
        implementation_groups_definition=[{"ref_id": "A"}, {"ref_id": "B"}],
    )

    def node(node_id, parent=None, groups=None, assessable=True):
        return RequirementNode.objects.create(
            framework=framework,
            urn=f"{NS}:{node_id}",
            ref_id=node_id.upper(),
            parent_urn=f"{NS}:{parent}" if parent else None,
            assessable=assessable,
            implementation_groups=groups,
            folder=folder,
        )

    node("one", assessable=False)
    node("two", assessable=False)
    nodes = {
        "r1": node("r1", "one", ["A"]),
        "r2": node("r2", "one", ["A", "B"]),
        "r3": node("r3", "two", ["B"]),
    }
    # Run the evaluations creation schedules: the test transaction never
    # commits, and a pending one would absorb the next.
    with django_capture_on_commit_callbacks(execute=True):
        ca = ComplianceAssessment.objects.create(
            name="Levels audit",
            framework=framework,
            folder=folder,
            min_score=1,
            max_score=5,
        )
        ca.show_documentation_score = True
        ca.save()
        ca.create_requirement_assessments()
    return {"framework": framework, "ca": ca, "nodes": nodes}


def _ra(levels, key) -> RequirementAssessment:
    return RequirementAssessment.objects.get(
        compliance_assessment=levels["ca"], requirement=levels["nodes"][key]
    )


def _score(levels, key, score, documentation=None, result="compliant"):
    RequirementAssessment.objects.filter(pk=_ra(levels, key).pk).update(
        score=score, documentation_score=documentation, is_scored=True, result=result
    )


def _rules(levels, rules):
    levels["framework"].outcomes_definition = rules
    levels["framework"].save(update_fields=["outcomes_definition"])


def _evaluate(levels) -> ComplianceAssessment:
    ca = ComplianceAssessment.objects.get(pk=levels["ca"].pk)
    evaluate_outcomes(ca)
    ca.refresh_from_db()
    return ca


@pytest.mark.django_db
class TestOrderedRules:
    def test_a_yes_no_rule_reads_the_rules_above_it(self, levels):
        _rules(
            levels,
            [
                {"ref_id": "a", "expression": "true"},
                {"ref_id": "b", "expression": '"a" in computed_outcomes'},
                {"ref_id": "c", "expression": '"d" in computed_outcomes'},
                {"ref_id": "d", "expression": "true"},
            ],
        )
        assert set(_evaluate(levels).computed_outcome) == {"a", "b", "d"}

    def test_number_rules_are_computed_and_stored(self, levels):
        _score(levels, "r1", 4, 2)
        _rules(
            levels,
            [
                {
                    "ref_id": "double",
                    "kind": "number",
                    "expression": 'requirements["r1"].maturity_score * 2.0',
                },
                {"ref_id": "high", "expression": "values.double >= 6.0"},
            ],
        )
        ca = _evaluate(levels)
        assert ca.computed_values == {"double": 6.0}
        assert set(ca.computed_outcome) == {"high"}

    def test_no_values_without_number_rules(self, levels):
        _rules(levels, [{"ref_id": "a", "expression": "true"}])
        assert _evaluate(levels).computed_values is None


@pytest.mark.django_db
class TestRulesLimitedToGroups:
    RULES = [
        {"ref_id": "on_a", "implementation_groups": ["A"], "expression": "true"},
        {"ref_id": "on_b", "implementation_groups": ["B"], "expression": "true"},
        {"ref_id": "always", "expression": "true"},
    ]

    @pytest.mark.parametrize(
        "selected, fired",
        [
            ([], {"on_a", "on_b", "always"}),
            (["A"], {"on_a", "always"}),
            (["B"], {"on_b", "always"}),
        ],
    )
    def test_a_rule_applies_when_its_group_is_in_scope(self, levels, selected, fired):
        _rules(levels, self.RULES)
        ComplianceAssessment.objects.filter(pk=levels["ca"].pk).update(
            selected_implementation_groups=selected
        )
        assert set(_evaluate(levels).computed_outcome) == fired

    def test_the_group_scope_is_not_passed_on(self, levels):
        _rules(levels, self.RULES)
        assert "implementation_groups" not in _evaluate(levels).computed_outcome["on_a"]

    def test_no_rule_in_scope_clears_the_outcomes(self, levels):
        _rules(levels, self.RULES[:1])
        ComplianceAssessment.objects.filter(pk=levels["ca"].pk).update(
            selected_implementation_groups=["B"], computed_outcome={"stale": {}}
        )
        assert _evaluate(levels).computed_outcome is None


@pytest.mark.django_db
class TestScoresInTheContext:
    def _context(self, levels, expression):
        ca = ComplianceAssessment.objects.get(pk=levels["ca"].pk)
        context, _ = build_cel_context(ca)
        _add_scores(context, ca, ca.framework, [{"expression": expression}])
        return ca, context

    def test_requirements_carry_documentation_and_maturity(self, levels):
        _score(levels, "r1", 4, 2)
        _score(levels, "r2", 4)
        _, context = self._context(levels, "true")
        assert context["requirements"]["r1"]["documentation_score"] == 2
        assert context["requirements"]["r1"]["maturity_score"] == 3.0
        # An unset documentation score counts as the bottom of the scale.
        assert context["requirements"]["r2"]["maturity_score"] == 2.5
        assert context["requirements"]["r2"]["implementation_groups"] == ["A", "B"]
        # Unscored counts for nothing, as in the audit's aggregates.
        assert context["requirements"]["r3"]["maturity_score"] == -1.0

    def test_not_applicable_counts_at_the_target_when_the_audit_says_so(self, levels):
        _score(levels, "r1", 2, 2, result="not_applicable")
        ComplianceAssessment.objects.filter(pk=levels["ca"].pk).update(
            anchor_na_to_target=True, target_score=3
        )
        _, context = self._context(levels, "true")
        assert context["requirements"]["r1"]["maturity_score"] == 3.0
        ComplianceAssessment.objects.filter(pk=levels["ca"].pk).update(
            anchor_na_to_target=False
        )
        _, context = self._context(levels, "true")
        assert context["requirements"]["r1"]["maturity_score"] == -1.0

    def test_the_audit_scores_are_the_ones_it_shows(self, levels):
        _score(levels, "r1", 4, 2)
        _score(levels, "r3", 5, 5)
        ca, context = self._context(levels, "true")
        shown = ca.get_global_score()
        for layer in ("implementation_score", "documentation_score", "maturity_score"):
            assert context["assessment"][layer] == pytest.approx(shown[layer])
        assert context["assessment"]["target_score"] == 5.0

    def test_rules_read_unrounded_scores(self, levels):
        # As in the CCB tools, where 2.997 shows as 3.00 but misses a 3.0 target.
        for key, score in (("r1", 4), ("r2", 4), ("r3", 5)):
            _score(levels, key, score)
        _rules(
            levels,
            [
                {
                    "ref_id": "above",
                    "expression": "assessment.implementation_score > 4.333",
                }
            ],
        )
        assert _evaluate(levels).computed_outcome == {"above": {}}

    def test_nothing_scored_reads_minus_one(self, levels):
        _, context = self._context(levels, "sections")
        assert context["assessment"]["maturity_score"] == -1.0
        assert context["sections"]["one"]["maturity_score"] == -1.0

    def test_sections_and_groups_score_their_requirements(self, levels):
        _score(levels, "r1", 4, 2)
        _score(levels, "r2", 2, 2)
        _score(levels, "r3", 5, 5)
        ca, context = self._context(levels, "sections.size() + groups.size()")
        one = ca.get_scores_for([_ra(levels, "r1"), _ra(levels, "r2")])
        assert context["sections"]["one"]["maturity_score"] == one["maturity_score"]
        assert context["sections"]["one"]["depth"] == 1
        assert context["sections"]["one"]["ref_id"] == "ONE"
        assert context["sections"]["one"]["total_count"] == 2
        b = ca.get_scores_for([_ra(levels, "r2"), _ra(levels, "r3")])
        assert context["groups"]["B"]["maturity_score"] == b["maturity_score"]

    def test_sections_and_groups_only_when_a_rule_reads_them(self, levels):
        _, context = self._context(levels, 'requirements["r1"].score > 0')
        assert "sections" not in context and "groups" not in context

    def test_out_of_scope_requirements_are_left_out(self, levels):
        ComplianceAssessment.objects.filter(pk=levels["ca"].pk).update(
            selected_implementation_groups=["A"]
        )
        _, context = self._context(levels, "sections.size() + groups.size()")
        assert context["groups"]["B"]["total_count"] == 1
        # Present like in the builder's checks, scoring nothing.
        assert context["sections"]["two"]["total_count"] == 0
        assert context["sections"]["two"]["maturity_score"] == -1.0

    def test_a_rule_on_an_empty_group_fails_instead_of_erroring(self, levels):
        ComplianceAssessment.objects.filter(pk=levels["ca"].pk).update(
            selected_implementation_groups=["A"]
        )
        _rules(
            levels,
            [
                {
                    "ref_id": "n",
                    "kind": "number",
                    "expression": 'sections["two"].maturity_score',
                },
                {"ref_id": "low", "expression": "values.n < 0.0"},
            ],
        )
        ca = _evaluate(levels)
        assert ca.computed_values == {"n": -1.0}
        assert set(ca.computed_outcome) == {"low"}

    def test_the_names_are_the_ones_the_builder_suggests(self, levels):
        if not FIELDS.exists():
            pytest.skip("frontend sources not checked out")
        fields = json.loads(FIELDS.read_text())["framework"]
        _, context = self._context(levels, "sections.size() + groups.size()")
        assert set(context["assessment"]) == {
            *fields["assessment"],
            *fields["assessment_scores"],
        }
        assert set(context["requirements"]["r1"]) == set(fields["requirements"])
        assert set(context["sections"]["one"]) == set(fields["sections"])
        assert set(context["groups"]["A"]) == set(fields["groups"])


@pytest.mark.django_db
class TestReEvaluation:
    RULES = [
        {
            "ref_id": "documented",
            "expression": 'requirements["r1"].maturity_score > 4.0',
        },
        {"ref_id": "on_b", "implementation_groups": ["B"], "expression": "true"},
    ]

    def test_a_documentation_score_change(
        self, levels, django_capture_on_commit_callbacks
    ):
        _rules(levels, self.RULES)
        _score(levels, "r1", 4, 2)
        assert "documented" not in _evaluate(levels).computed_outcome
        ra = _ra(levels, "r1")
        ra.documentation_score = 5
        with django_capture_on_commit_callbacks(execute=True):
            ra.save(update_fields=["documentation_score"])
        levels["ca"].refresh_from_db()
        assert "documented" in levels["ca"].computed_outcome

    def test_a_scope_change(self, levels, django_capture_on_commit_callbacks):
        _rules(levels, self.RULES)
        assert "on_b" in _evaluate(levels).computed_outcome
        ca = ComplianceAssessment.objects.get(pk=levels["ca"].pk)
        ca.selected_implementation_groups = ["A"]
        with django_capture_on_commit_callbacks(execute=True):
            ca.save()
        ca.refresh_from_db()
        assert "on_b" not in ca.computed_outcome

    def test_turning_documentation_scoring_off(
        self, levels, django_capture_on_commit_callbacks
    ):
        _rules(levels, self.RULES)
        _score(levels, "r1", 4, 5)
        assert "documented" in _evaluate(levels).computed_outcome
        ca = ComplianceAssessment.objects.get(pk=levels["ca"].pk)
        ca.show_documentation_score = False
        with django_capture_on_commit_callbacks(execute=True):
            ca.save()
        ca.refresh_from_db()
        assert "documented" not in ca.computed_outcome

    def test_a_new_audit(self, levels, django_capture_on_commit_callbacks):
        _rules(levels, self.RULES)
        with django_capture_on_commit_callbacks(execute=True):
            ca = ComplianceAssessment.objects.create(
                name="New", framework=levels["framework"], folder=levels["ca"].folder
            )
        ca.refresh_from_db()
        assert ca.computed_outcome == {"on_b": {}}

    def test_the_audit_is_read_when_the_evaluation_runs(
        self, levels, django_capture_on_commit_callbacks
    ):
        _rules(levels, self.RULES)
        assert "on_b" in _evaluate(levels).computed_outcome
        ca = ComplianceAssessment.objects.get(pk=levels["ca"].pk)
        with django_capture_on_commit_callbacks(execute=True):
            ca.selected_implementation_groups = ["B"]
            ca.save()
            # Changed again later in the same transaction, like a library update does.
            ComplianceAssessment.objects.filter(pk=ca.pk).update(
                selected_implementation_groups=["A"]
            )
        ca.refresh_from_db()
        assert "on_b" not in ca.computed_outcome

    def test_a_field_left_out_of_a_partial_save_is_still_detected(
        self, levels, django_capture_on_commit_callbacks
    ):
        _rules(levels, self.RULES)
        assert "on_b" in _evaluate(levels).computed_outcome
        ca = ComplianceAssessment.objects.get(pk=levels["ca"].pk)
        ca.selected_implementation_groups = ["A"]
        ca.target_score = 4
        with django_capture_on_commit_callbacks(execute=True):
            ca.save(update_fields=["target_score"])
        with django_capture_on_commit_callbacks(execute=True):
            ca.save(update_fields=["selected_implementation_groups"])
        ca.refresh_from_db()
        assert "on_b" not in ca.computed_outcome

    def test_a_rolled_back_change_does_not_block_the_next(
        self, levels, django_capture_on_commit_callbacks
    ):
        _rules(levels, self.RULES)
        assert "on_b" in _evaluate(levels).computed_outcome
        ca = ComplianceAssessment.objects.get(pk=levels["ca"].pk)

        def change_then_fail():
            with transaction.atomic():
                ca.selected_implementation_groups = ["B"]
                ca.save()
                raise RuntimeError

        with pytest.raises(RuntimeError):
            change_then_fail()
        ca = ComplianceAssessment.objects.get(pk=levels["ca"].pk)
        with django_capture_on_commit_callbacks(execute=True):
            ca.selected_implementation_groups = ["A"]
            ca.save()
        ca.refresh_from_db()
        assert "on_b" not in ca.computed_outcome

    def test_a_library_update_with_a_broken_rule_is_refused(self):
        StoredLibrary.store_library_content(_library(1, "before").encode())[0].load()
        StoredLibrary.store_library_content(
            _library(2, "after")
            .replace('"true"', 'requirements["missing"].score > 0')
            .encode()
        )
        error = LoadedLibrary.objects.get(urn="urn:test:risk:library:updated").update()
        assert error and "No requirement 'missing'" in error
        framework = Framework.objects.get(urn="urn:test:risk:framework:updated")
        assert [rule["ref_id"] for rule in framework.outcomes_definition] == ["before"]

    def test_a_library_update(self, django_capture_on_commit_callbacks):
        StoredLibrary.store_library_content(_library(1, "before").encode())[0].load()
        with django_capture_on_commit_callbacks(execute=True):
            ca = ComplianceAssessment.objects.create(
                name="Updated",
                framework=Framework.objects.get(urn="urn:test:risk:framework:updated"),
                folder=Folder.get_root_folder(),
            )
        ca.refresh_from_db()
        assert set(ca.computed_outcome) == {"before"}
        StoredLibrary.store_library_content(_library(2, "after").encode())
        with django_capture_on_commit_callbacks(execute=True):
            assert (
                LoadedLibrary.objects.get(urn="urn:test:risk:library:updated").update()
                is None
            )
        ca.refresh_from_db()
        assert set(ca.computed_outcome) == {"after"}


def _library(version: int, rule: str) -> str:
    return f"""
urn: urn:test:risk:library:updated
locale: en
ref_id: updated
name: Updated
version: {version}
provider: test
packager: test
objects:
  framework:
    urn: urn:test:risk:framework:updated
    ref_id: updated
    name: Updated
    outcomes_definition:
    - ref_id: {rule}
      expression: "true"
    requirement_nodes:
    - urn: {NS}:updated
      assessable: true
"""


class TestValidation:
    FRAMEWORK = {
        "implementation_groups_definition": [{"ref_id": "A"}],
        "requirement_nodes": [
            {"urn": f"{NS}:one", "assessable": False, "depth": 1},
            {"urn": f"{NS}:r1", "parent_urn": f"{NS}:one", "assessable": True},
        ],
    }

    def _errors(self, rules=(), visibility=None):
        framework = {**self.FRAMEWORK, "outcomes_definition": list(rules)}
        if visibility:
            framework["requirement_nodes"] = [
                *framework["requirement_nodes"],
                {
                    "urn": f"{NS}:r2",
                    "assessable": True,
                    "visibility_expression": visibility,
                },
            ]
        return [e["error"] for e in validate_framework_expressions(framework)]

    def test_the_new_names_are_accepted(self):
        assert (
            self._errors(
                [
                    {
                        "ref_id": "avg",
                        "kind": "number",
                        "expression": 'groups["A"].maturity_score',
                    },
                    {
                        "ref_id": "ok",
                        "implementation_groups": ["A"],
                        "expression": 'values.avg >= assessment.target_score && sections["one"].depth == 1',
                    },
                    {"ref_id": "all", "expression": '"ok" in computed_outcomes'},
                ]
            )
            == []
        )

    def test_a_rule_reads_only_the_yes_no_rules_above_it(self):
        errors = self._errors(
            [
                {"ref_id": "a", "expression": '"b" in computed_outcomes'},
                {"ref_id": "b", "expression": "true"},
            ]
        )
        assert errors == [
            "No yes/no rule 'b' above this one: a rule reads only the yes/no "
            "rules listed before it"
        ]

    def test_unknown_groups_and_sections(self):
        errors = self._errors(
            [
                {"ref_id": "a", "implementation_groups": ["Z"], "expression": "true"},
                {"ref_id": "b", "expression": 'sections["nope"].depth == 1'},
            ]
        )
        assert errors[0] == "Unknown implementation group 'Z'"
        assert errors[1].startswith("No section 'nope' in this framework")

    @pytest.mark.parametrize(
        "expression", ["assessment.maturity_score > 1.0", 'sections["one"].depth == 1']
    )
    def test_visibility_cannot_read_the_scores(self, expression):
        assert len(self._errors(visibility=expression)) == 1


@pytest.mark.django_db
def test_a_library_with_an_invalid_rule_does_not_load():
    content = f"""
urn: urn:test:risk:library:bad-rule
locale: en
ref_id: bad-rule
name: Bad rule
version: 1
provider: test
packager: test
objects:
  framework:
    urn: urn:test:risk:framework:bad-rule
    ref_id: bad-rule
    name: Bad rule
    outcomes_definition:
    - ref_id: broken
      expression: requirements["missing"].score > 0
    requirement_nodes:
    - urn: {NS}:bad
      assessable: true
      depth: 1
"""
    stored, error = StoredLibrary.store_library_content(content.encode())
    assert error is None
    error = stored.load()
    assert error and "No requirement 'missing'" in error
    assert not Framework.objects.filter(urn="urn:test:risk:framework:bad-rule").exists()


@pytest.fixture
def cyfun(db):
    stored = StoredLibrary.objects.filter(
        urn="urn:intuitem:risk:library:ccb-cyfun2025"
    ).first()
    if stored is None:
        stored, error = StoredLibrary.store_library_content(CYFUN.read_bytes())
        assert error is None
    assert stored.version == 10
    assert stored.load() is None
    framework = Framework.objects.get(urn="urn:intuitem:risk:framework:ccb-cyfun2025")

    def audit(groups, score=4, documentation=4):
        ca = ComplianceAssessment.objects.create(
            name="CyFun",
            framework=framework,
            folder=Folder.get_root_folder(),
            min_score=1,
            max_score=5,
            score_calculation_method="average_of_averages",
            selected_implementation_groups=groups,
        )
        ca.show_documentation_score = True
        ca.save()
        ca.create_requirement_assessments()
        RequirementAssessment.objects.filter(compliance_assessment=ca).update(
            score=score,
            documentation_score=documentation,
            is_scored=True,
            result="compliant",
        )
        return ca

    return audit


def _not_applicable(ca, group, count=1):
    ids = RequirementAssessment.objects.filter(
        compliance_assessment=ca, requirement__assessable=True
    ).values_list("id", "requirement__implementation_groups")
    picked = [pk for pk, groups in ids if group(groups or [])][:count]
    RequirementAssessment.objects.filter(id__in=picked).update(result="not_applicable")


def _outcomes(ca) -> set[str]:
    evaluate_outcomes(ca)
    ca.refresh_from_db()
    return set(ca.computed_outcome or {})


@pytest.mark.django_db
class TestCyfunConformityCriteria:
    def test_the_library_rules_are_valid(self, cyfun):
        framework = Framework.objects.get(
            urn="urn:intuitem:risk:framework:ccb-cyfun2025"
        )
        assert len(framework.outcomes_definition) == 13

    def test_an_audit_shows_only_its_level(self, cyfun):
        fired = _outcomes(cyfun(["I"]))
        assert fired == {
            "important_maturity",
            "important_key_measures",
            "important_exclusions",
            "important_criteria_met",
        }

    def test_the_whole_framework_is_checked_at_every_level(self, cyfun):
        fired = _outcomes(cyfun([]))
        assert len(fired) == 13

    @pytest.mark.parametrize(
        "score, met",
        [
            (3, {"basic", "important"}),
            (2, set()),
            (5, {"basic", "important", "essential"}),
        ],
    )
    def test_maturity_targets(self, cyfun, score, met):
        fired = _outcomes(cyfun([], score=score, documentation=score))
        assert {r.split("_")[0] for r in fired if r.endswith("_criteria_met")} == met

    def test_an_excluded_key_measure_fails_the_level(self, cyfun):
        ca = cyfun(["B"])
        _not_applicable(ca, lambda groups: "BK" in groups)
        fired = _outcomes(ca)
        assert "basic_exclusions" not in fired
        assert "basic_criteria_met" not in fired
        assert "basic_maturity" in fired

    def test_exclusions_are_counted_per_level(self, cyfun):
        ca = cyfun(["I"])
        _not_applicable(
            ca, lambda groups: "I" in groups and not {"IK", "IG"} & set(groups), 3
        )
        assert "important_exclusions" in _outcomes(ca)
        _not_applicable(
            ca, lambda groups: "I" in groups and not {"IK", "IG"} & set(groups), 4
        )
        assert "important_exclusions" not in _outcomes(ca)

    def test_a_weak_category_fails_essential(self, cyfun):
        ca = cyfun(["E"])
        category = RequirementNode.objects.get(
            urn="urn:intuitem:risk:req_node:ccb-cyfun2025:gv.oc"
        )
        RequirementAssessment.objects.filter(
            compliance_assessment=ca,
            requirement__parent_urn__startswith=category.urn,
            requirement__assessable=True,
        ).update(score=1, documentation_score=1)
        fired = _outcomes(ca)
        assert "essential_categories" not in fired
        assert "essential_criteria_met" not in fired
