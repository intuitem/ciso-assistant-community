"""Variable defaults: stored by the graph API, seeded into every run, and
checked against the variable's type at publish."""

import uuid

import pytest

from iam.models import Folder
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph, serialize_graph
from automation.workflows.models import Workflow, WorkflowVersion
from automation.workflows.tests.helpers import publisher_user
from automation.workflows.validation import validate_graph


def node(type_, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(source, target):
    return {"id": str(uuid.uuid4()), "source": source["id"], "target": target["id"]}


def var(key, type_, default):
    return {
        "id": str(uuid.uuid4()),
        "key": key,
        "type": type_,
        "default_value": default,
    }


def build(variables):
    workflow = Workflow.objects.create(name="Defaults", folder=Folder.get_root_folder())
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", trigger_config={"type": "manual"})
    end = node("end")
    save_graph(
        version,
        {"nodes": [start, end], "edges": [edge(start, end)], "variables": variables},
    )
    return version


def codes(version):
    return {error["code"] for error in validate_graph(version)}


@pytest.mark.django_db
class TestDefaults:
    def test_defaults_round_trip_through_the_graph_and_seed_the_run(self):
        version = build(
            [
                var("notify", "string", "approvals@example.com"),
                var("threshold", "number", 4),
                var("ratio", "number", 2.5),
                var("strict", "boolean", False),
                var("since", "date", "2026-10-02"),
                var("options", "json", {"a": [1, 2]}),
                var("unset", "string", None),
            ]
        )
        stored = {
            v["key"]: v["default_value"] for v in serialize_graph(version)["variables"]
        }
        assert stored == {
            "notify": "approvals@example.com",
            "threshold": 4,
            "ratio": 2.5,
            "strict": False,
            "since": "2026-10-02",
            "options": {"a": [1, 2]},
            "unset": None,
        }
        instance = start_instance(version)
        for key, value in stored.items():
            assert instance.variables[key] == value

    def test_typed_defaults_publish_clean(self):
        version = build(
            [
                var("threshold", "number", 4),
                var("strict", "boolean", False),
                var("since", "date", "2026-10-02"),
                var("options", "json", [1, 2]),
                var("unset", "number", None),
            ]
        )
        assert "variable_default_invalid" not in codes(version)

    def test_a_default_of_the_wrong_type_is_caught_at_publish(self):
        # What a hand-written YAML or an older editor could produce.
        version = build(
            [
                var("threshold", "number", "abc"),
                var("strict", "boolean", "yes"),
                var("since", "date", "next tuesday"),
            ]
        )
        errors = [
            e
            for e in validate_graph(version)
            if e["code"] == "variable_default_invalid"
        ]
        assert {e["message"].split("'")[1] for e in errors} == {
            "threshold",
            "strict",
            "since",
        }

    def test_a_numeric_string_default_on_a_number_is_tolerated(self):
        # coerce_variable_value accepts "4" for a number the way the run
        # dialog does; publish follows the same rule rather than a stricter one.
        version = build([var("threshold", "number", "4")])
        assert "variable_default_invalid" not in codes(version)
        # ...and the run gets the number, not the string publish accepted.
        assert start_instance(version).variables["threshold"] == 4

    def test_an_empty_default_seeds_null_outside_strings(self):
        version = build([var("threshold", "number", ""), var("label", "string", "")])
        assert "variable_default_invalid" not in codes(version)
        variables = start_instance(version).variables
        assert variables["threshold"] is None
        assert variables["label"] == ""

    def test_a_non_finite_number_default_is_caught_at_publish(self):
        version = build([var("threshold", "number", "nan")])
        assert "variable_default_invalid" in codes(version)
