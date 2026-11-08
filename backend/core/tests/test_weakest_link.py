from pathlib import Path

import pytest
import yaml

from core.cel_service import (
    evaluate_outcomes,
    validate_framework_expressions,
    validate_quick_form_expressions,
)
from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from core.weakest_link import (
    compute_weakest_link,
    evaluate_weakest_links,
    weakest_link_errors,
    weakest_link_rules,
)
from iam.models import Folder
from library.utils import QuickFormImporter

RULE = {"ref_id": "eff", "kind": "weakest_link", "rated_depth": 2, "per": "depth_1"}


def tree(spec):
    """spec: {domain: {principle: [action, ...]}} -> nodes in tree order."""
    nodes = []
    for domain, principles in spec.items():
        nodes.append({"urn": domain, "parent_urn": None, "assessable": False})
        for principle, actions in principles.items():
            nodes.append({"urn": principle, "parent_urn": domain, "assessable": False})
            nodes += [
                {"urn": a, "parent_urn": principle, "assessable": True} for a in actions
            ]
    return nodes


def run(spec, results, rule=RULE):
    ras = {urn: (urn, result) for urn, result in results.items()}
    return compute_weakest_link(rule, tree(spec), ras)


def ratings(section):
    return {n["urn"]: n["rating"] for n in section["nodes"]}


def test_a_principle_takes_its_lowest_action():
    # ASD's example: four fully effective and two partially effective actions.
    actions = [f"a{i}" for i in range(6)]
    out = run(
        {"id": {"p": actions}},
        {
            a: "partially_compliant" if a in ("a1", "a4") else "compliant"
            for a in actions
        },
    )
    (section,) = out["sections"]
    assert ratings(section) == {"p": "partially_compliant"}
    assert [d["urn"] for d in section["nodes"][0]["drivers"]] == ["a1", "a4"]


def test_one_unassessed_action_leaves_the_principle_unassessed():
    out = run({"d": {"p": ["a", "b"]}}, {"a": "non_compliant", "b": "not_assessed"})
    node = out["sections"][0]["nodes"][0]
    assert node["rating"] == "not_assessed"
    assert [d["urn"] for d in node["drivers"]] == ["b"]


def test_not_applicable_actions_are_set_aside():
    out = run(
        {"d": {"p": ["a", "b"], "q": ["c"]}},
        {"a": "not_applicable", "b": "compliant", "c": "not_applicable"},
    )
    assert ratings(out["sections"][0]) == {"p": "compliant", "q": "not_applicable"}
    assert out["sections"][0]["score"] == 1.0
    assert out["sections"][0]["counts"] == {
        "compliant": 1,
        "partially_compliant": 0,
        "non_compliant": 0,
        "not_assessed": 0,
    }


def test_domain_score_is_asd_percentage():
    # ASD's example: 5 fully, 4 partially and 1 not effective -> 70%.
    principles = {f"p{i}": [f"a{i}"] for i in range(10)}
    results = {f"a{i}": "compliant" for i in range(5)}
    results |= {f"a{i}": "partially_compliant" for i in range(5, 9)}
    results["a9"] = "non_compliant"
    (section,) = run({"vr": principles}, results)["sections"]
    assert section["score"] == pytest.approx(0.7)
    assert section["counts"] == {
        "compliant": 5,
        "partially_compliant": 4,
        "non_compliant": 1,
        "not_assessed": 0,
    }


def test_unassessed_principles_score_0_and_an_unassessed_domain_has_no_score():
    out = run(
        {"d1": {"p": ["a"], "q": ["b"]}, "d2": {"r": ["c"]}},
        {"a": "compliant", "b": "not_assessed", "c": "not_assessed"},
    )
    d1, d2 = out["sections"]
    assert d1["score"] == 0.5 and d1["counts"]["not_assessed"] == 1
    assert d2["score"] is None
    assert out["score"] == 0.5


def test_not_assessed_lowers_the_score_and_not_applicable_does_not():
    spec = {"d": {"p": ["a"], "q": ["b"], "r": ["c"], "s": ["e"], "t": ["f"]}}
    results = dict.fromkeys(["a", "b", "c", "e", "f"], "compliant")

    def score(result):
        return run(spec, {**results, "f": result})["sections"][0]["score"]

    assert score("not_assessed") == score("non_compliant") == pytest.approx(0.8)
    assert score("not_applicable") == 1.0


def test_requirements_outside_the_audit_are_left_out():
    out = run({"d1": {"p": ["a"]}, "d2": {"q": ["b"]}}, {"a": "non_compliant"})
    assert [s["urn"] for s in out["sections"]] == ["d1"]
    assert out["score"] == 0.0


def test_whole_audit_and_custom_weights():
    rule = {
        "ref_id": "eff",
        "kind": "weakest_link",
        "rated_depth": 1,
        "result_weights": {"partially_compliant": 0.25},
    }
    out = run(
        {"d1": {"p": ["a"]}, "d2": {"q": ["b"]}},
        {"a": "compliant", "b": "partially_compliant"},
        rule,
    )
    (section,) = out["sections"]
    assert section["urn"] is None
    assert ratings(section) == {"d1": "compliant", "d2": "partially_compliant"}
    assert out["score"] == pytest.approx(0.625)


@pytest.mark.parametrize(
    "patch",
    [
        {"rated_depth": 0},
        {"rated_depth": "2"},
        {"per": "depth_2"},
        {"rated_depth": 1, "per": "depth_1"},
        {"result_weights": {"compliant": "one"}},
        {"result_weights": {"not_assessed": 0}},
        {"result_labels": ["Fully effective"]},
        {"rated_depth": -1, "per": None},
        {"result_weights": {"compliant": 2}},
        {"result_weights": {"non_compliant": -1}},
        {"result_weights": {"compliant": float("nan")}},
        {"result_labels": {"complaint": "Fully effective"}},
    ],
)
def test_invalid_rules_are_rejected(patch):
    framework = {
        "implementation_groups_definition": [],
        "outcomes_definition": [{**RULE, **patch}],
        "requirement_nodes": [],
    }
    assert validate_framework_expressions(framework)
    assert weakest_link_rules(framework["outcomes_definition"]) == []


def test_every_result_shown_can_be_named():
    labels = {
        result: result.title()
        for result in (
            "compliant",
            "partially_compliant",
            "non_compliant",
            "not_assessed",
            "not_applicable",
        )
    }
    assert weakest_link_errors({**RULE, "result_labels": labels}) == []


def test_quick_forms_refuse_the_rule():
    form = {"outcomes_definition": [RULE], "pages": []}
    assert any(
        e["ref_id"] == "eff" and "weakest-link" in e["error"].lower()
        for e in validate_quick_form_expressions(form)
    )


def test_asd_essentials_library_rule():
    path = (
        Path(__file__).resolve().parents[2]
        / "library/libraries/asd-essentials-enterprise-it.yaml"
    )
    framework = yaml.safe_load(path.read_text())["objects"]["framework"]
    assert validate_framework_expressions(framework) == []
    nodes = [
        {**n, "parent_urn": n.get("parent_urn")} for n in framework["requirement_nodes"]
    ]
    (rule,) = framework["outcomes_definition"]
    ras = {n["urn"]: (n["urn"], "compliant") for n in nodes if n["assessable"]}
    out = compute_weakest_link(rule, nodes, ras)
    assert [len(s["nodes"]) for s in out["sections"]] == [7, 10, 16, 16, 16, 16, 13, 10]
    assert out["score"] == 1.0


def test_library_publish_refuses_the_rule_in_a_quick_form():
    form = {
        "urn": "urn:test:risk:quick_form:wl",
        "ref_id": "wl",
        "outcomes_definition": [RULE],
        "pages": [
            {
                "urn": "urn:test:risk:qf_page:wl:p",
                "ref_id": "p",
                "questions": {
                    "urn:test:risk:qf_page:wl:p:question:q": {
                        "type": "text",
                        "text": "Q",
                    }
                },
            }
        ],
    }
    error = QuickFormImporter(form).init()
    assert error and "weakest-link" in error


def make_audit(results, **audit_fields):
    """results: {ref: (result, node fields)} under one domain and principle."""
    folder = Folder.get_root_folder()
    framework = Framework.objects.create(
        name="Weakest link",
        folder=folder,
        outcomes_definition=[
            {**RULE, "label": "Effectiveness"},
            {"ref_id": "half", "kind": "number", "expression": "values.eff / 2.0"},
        ],
    )
    base = "urn:intuitem:risk:req_node:wl"

    def node(ref, parent, **fields):
        return RequirementNode.objects.create(
            framework=framework,
            urn=f"{base}:{ref}",
            parent_urn=f"{base}:{parent}" if parent else None,
            assessable=parent == "p",
            folder=folder,
            **fields,
        )

    node("d", None)
    node("p", "d")
    audit = ComplianceAssessment.objects.create(
        name="WL",
        framework=framework,
        folder=folder,
        perimeter=Perimeter.objects.create(name="WL", folder=folder),
        **audit_fields,
    )
    for ref, (result, fields) in results.items():
        RequirementAssessment.objects.create(
            compliance_assessment=audit,
            requirement=node(ref, "p", **fields),
            folder=folder,
            result=result,
        )
    return audit, framework


@pytest.mark.django_db
def test_the_overall_score_is_stored_as_a_value_numbers_can_read():
    audit, framework = make_audit(
        {"a": ("partially_compliant", {}), "b": ("compliant", {})}
    )
    values, details = evaluate_weakest_links(audit, framework.outcomes_definition)
    assert values == {"eff": 50.0}
    assert details[0]["sections"][0]["urn"] == "urn:intuitem:risk:req_node:wl:d"
    evaluate_outcomes(audit)
    audit.refresh_from_db()
    assert audit.computed_values == {"eff": 50.0, "half": 25.0}


@pytest.mark.django_db
def test_requirements_outside_the_selected_groups_are_left_out():
    audit, _framework = make_audit(
        {
            "a": ("compliant", {"implementation_groups": ["1"]}),
            "b": ("non_compliant", {"implementation_groups": ["2"]}),
        },
        selected_implementation_groups=["1"],
    )
    evaluate_outcomes(audit)
    audit.refresh_from_db()
    assert audit.computed_values == {"eff": 100.0, "half": 50.0}


@pytest.mark.django_db
def test_hidden_requirements_are_left_out():
    audit, framework = make_audit(
        {
            "a": ("compliant", {}),
            "b": ("not_assessed", {"visibility_expression": "false"}),
        }
    )
    _values, details = evaluate_weakest_links(audit, framework.outcomes_definition)
    assert details[0]["sections"][0]["nodes"][0]["rating"] == "compliant"
    evaluate_outcomes(audit)
    audit.refresh_from_db()
    assert audit.computed_values == {"eff": 100.0, "half": 50.0}
