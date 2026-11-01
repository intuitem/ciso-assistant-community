from pathlib import Path

import pytest
import yaml

from core.cel_service import validate_framework_expressions
from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from core.staircase import (
    compute_staircase,
    evaluate_staircases,
    expand_scope,
    staircase_errors,
)
from iam.models import Folder

RULE = {
    "ref_id": "ml",
    "kind": "staircase",
    "levels": ["1", "2", "3"],
    "per": "depth_1",
}


def node(urn, parent=None, groups=None):
    return {
        "urn": f"urn:intuitem:risk:req_node:f:{urn}",
        "parent_urn": f"urn:intuitem:risk:req_node:f:{parent}" if parent else None,
        "ref_id": urn,
        "name": urn,
        "assessable": parent is not None,
        "implementation_groups": groups,
    }


# Two strategies; "a" lists a statement replaced at ML3 (tagged 1,2) as E8 does.
NODES = [
    node("a"),
    node("a1", "a", ["1", "2"]),
    node("a2", "a", ["2", "3"]),
    node("a3", "a", ["3"]),
    node("b"),
    node("b1", "b", ["1", "2", "3"]),
    node("b2", "b", ["3"]),
]


def run(results, rule=RULE):
    ras = {f"urn:intuitem:risk:req_node:f:{k}": (k, v) for k, v in results.items()}
    return compute_staircase(rule, NODES, ras)


def levels(out):
    return {u["node_id"]: u["level"] for u in out["units"]}


ALL_MET = {k: "compliant" for k in ("a1", "a2", "a3", "b1", "b2")}


def test_all_met():
    out = run(ALL_MET)
    assert levels(out) == {"a": 3, "b": 3} and out["level"] == 3


def test_failing_lowest_level_gives_zero_even_if_higher_met():
    out = run({**ALL_MET, "a1": "non_compliant"})
    assert levels(out)["a"] == 0
    unit = out["units"][0]
    assert unit["levels"] == {"1": "not_met", "2": "not_met", "3": "met"}
    assert [b["ref_id"] for b in unit["blocking"]] == ["a1"]
    assert out["level"] == 0


def test_listed_tags_are_not_cumulative():
    # a1 only counts up to ML2: failing it does not affect ML3's own set.
    out = run({**ALL_MET, "a2": "partially_compliant"})
    assert out["units"][0]["levels"] == {"1": "met", "2": "not_met", "3": "not_met"}
    assert levels(out)["a"] == 1


def test_not_applicable_passes_and_partial_fails():
    assert levels(run({**ALL_MET, "b2": "not_applicable"}))["b"] == 3
    assert levels(run({**ALL_MET, "b2": "partially_compliant"}))["b"] == 2


def test_unassessed_is_pending():
    out = run({**ALL_MET, "a3": "not_assessed"})
    assert out["units"][0]["levels"]["3"] == "pending"
    assert out["units"][0]["progress"]["3"] == [1, 2]
    assert levels(out)["a"] == 2


def test_overall_is_minimum():
    assert run({**ALL_MET, "b2": "non_compliant"})["level"] == 2


def test_requirements_outside_the_audit_are_out_of_scope():
    out = run({"a1": "compliant", "b1": "compliant"})
    assert out["units"][0]["levels"] == {
        "1": "met",
        "2": "out_of_scope",
        "3": "out_of_scope",
    }
    assert out["units"][0]["blocking"] == []


def test_cumulative_and_whole_audit():
    rule = {
        "ref_id": "ml",
        "kind": "staircase",
        "levels": ["1", "2"],
        "cumulative": True,
    }
    nodes_results = {**ALL_MET, "a1": "non_compliant"}
    out = run(nodes_results, rule)
    assert len(out["units"]) == 1 and out["units"][0]["node_id"] is None
    assert out["units"][0]["levels"] == {"1": "not_met", "2": "not_met"}


def test_expand_scope_pulls_lower_levels():
    assert sorted(expand_scope([RULE], ["3"])) == ["1", "2", "3"]
    assert expand_scope([RULE], ["1"]) == ["1"]
    assert expand_scope([], ["3"]) == ["3"]
    assert expand_scope([RULE], []) == []


def test_essential_eight_library_rule_validates():
    path = (
        Path(__file__).resolve().parents[2]
        / "library/libraries/essential-eight-2023.yaml"
    )
    framework = yaml.safe_load(path.read_text())["objects"]["framework"]
    assert validate_framework_expressions(framework) == []
    bad = {**framework, "outcomes_definition": [{**RULE, "levels": ["1", "9"]}]}
    assert validate_framework_expressions(bad)
    nodes = [
        {**n, "parent_urn": n.get("parent_urn")} for n in framework["requirement_nodes"]
    ]
    rule = framework["outcomes_definition"][0]
    out = compute_staircase(rule, nodes, {})
    assert out["units"] == []  # nothing in scope without requirement assessments
    in_scope = {n["urn"]: (n["urn"], "compliant") for n in nodes if n.get("assessable")}
    out = compute_staircase(rule, nodes, in_scope)
    assert len(out["units"]) == 8 and out["level"] == 3
    assert len(in_scope) == 152


def test_failed_requirement_with_missing_row_at_same_level():
    out = run({"a1": "non_compliant", "b1": "compliant"})
    assert out["units"][0]["levels"] == {
        "1": "not_met",
        "2": "out_of_scope",
        "3": "out_of_scope",
    }


def test_duplicate_levels_and_non_boolean_cumulative_are_rejected():
    groups = {"1", "2", "3"}
    assert staircase_errors({**RULE, "levels": ["1", "1"]}, groups)
    assert staircase_errors({**RULE, "cumulative": "false"}, groups)
    assert staircase_errors({**RULE, "cumulative": True}, groups) == []


def test_yes_no_rule_cannot_read_a_staircase_as_an_outcome():
    framework = {
        "implementation_groups_definition": [{"ref_id": g} for g in ("1", "2", "3")],
        "requirement_nodes": [],
        "outcomes_definition": [
            RULE,
            {"ref_id": "flag", "expression": '"ml" in computed_outcomes'},
            {"ref_id": "high", "expression": "values.ml >= 2.0"},
        ],
    }
    errors = validate_framework_expressions(framework)
    assert [e["ref_id"] for e in errors] == ["flag"]


@pytest.mark.django_db
def test_requirements_outside_the_selected_groups_are_out_of_scope():
    folder = Folder.get_root_folder()
    framework = Framework.objects.create(
        name="Staircase", folder=folder, min_score=0, max_score=100
    )
    tags = {"s": None, "s1": ["1", "2"], "s2": ["2"], "s3": ["3"]}
    nodes = {
        ref: RequirementNode.objects.create(
            framework=framework,
            urn=f"urn:intuitem:risk:req_node:sc:{ref}",
            parent_urn=None if ref == "s" else "urn:intuitem:risk:req_node:sc:s",
            ref_id=ref,
            assessable=ref != "s",
            implementation_groups=groups,
            folder=folder,
        )
        for ref, groups in tags.items()
    }
    audit = ComplianceAssessment.objects.create(
        name="ML1",
        framework=framework,
        folder=folder,
        perimeter=Perimeter.objects.create(name="Staircase", folder=folder),
        min_score=0,
        max_score=100,
        selected_implementation_groups=["1"],
    )
    for ref, node in nodes.items():
        RequirementAssessment.objects.create(
            compliance_assessment=audit,
            requirement=node,
            folder=folder,
            result="compliant" if ref == "s1" else "not_assessed",
        )
    values, details = evaluate_staircases(audit, [RULE])
    assert values == {"ml": 1.0}
    assert details[0]["units"][0]["levels"] == {
        "1": "met",
        "2": "out_of_scope",
        "3": "out_of_scope",
    }
