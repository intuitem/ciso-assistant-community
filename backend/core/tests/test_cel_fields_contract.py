"""The builder suggests CEL names from `cel-fields.json`; they must be the names
the evaluators provide, or authors are offered expressions the save refuses."""

import json
from pathlib import Path

import pytest

from core.cel_service import (
    _framework_probe,
    _framework_visibility_probe,
    _quick_form_probe,
)

FIELDS = (
    Path(__file__).resolve().parents[3]
    / "frontend/src/lib/components/FrameworkBuilder/cel-fields.json"
)

QUICK_FORM = {
    "outcomes_definition": [
        {"ref_id": "n", "kind": "number", "expression": "1"},
        {"ref_id": "b", "expression": "true"},
    ],
    "pages": [
        {
            "urn": "urn:t:risk:qf_page:f:p",
            "questions": {"urn:t:risk:qf_page:f:p:question:q": {"type": "boolean"}},
        }
    ],
}
FRAMEWORK = {
    "outcomes_definition": [
        {"ref_id": "n", "kind": "number", "expression": "1"},
        {"ref_id": "b", "expression": "true"},
    ],
    "implementation_groups_definition": [{"ref_id": "g"}],
    "requirement_nodes": [
        {"urn": "urn:t:risk:req_node:f:s", "assessable": False, "depth": 1},
        {
            "urn": "urn:t:risk:req_node:f:r",
            "parent_urn": "urn:t:risk:req_node:f:s",
            "assessable": True,
            "questions": {"urn:t:risk:req_node:f:r:question:q": {"type": "text"}},
        },
    ],
}


@pytest.fixture(scope="module")
def fields():
    if not FIELDS.exists():
        pytest.skip("frontend sources not checked out")
    return json.loads(FIELDS.read_text())


def test_quick_form_names_match_the_evaluator(fields):
    probe = _quick_form_probe(QUICK_FORM)
    expected = fields["quick_form"]
    assert set(expected["roots"]) == set(probe)
    assert set(expected["visibility_roots"]) == set(probe) - {"values"}
    assert set(expected["response"]) == set(probe["response"])
    assert set(expected["pages"]) == set(probe["pages"]["p"])
    assert set(expected["answers"]) == set(probe["answers"]["p:question:q"])


def test_framework_names_match_the_evaluator(fields):
    probe = _framework_probe(FRAMEWORK)
    visibility = _framework_visibility_probe(probe)
    expected = fields["framework"]
    assert set(expected["roots"]) == set(probe)
    assert set(expected["visibility_roots"]) == set(visibility)
    assert set(expected["assessment"]) == set(visibility["assessment"])
    assert set(expected["assessment_scores"]) == set(probe["assessment"]) - set(
        visibility["assessment"]
    )
    assert set(expected["requirements"]) == set(probe["requirements"]["r"])
    assert set(expected["sections"]) == set(probe["sections"]["s"])
    assert set(expected["groups"]) == set(probe["groups"]["g"])
    assert set(expected["answers"]) == set(probe["answers"]["r:question:q"])
