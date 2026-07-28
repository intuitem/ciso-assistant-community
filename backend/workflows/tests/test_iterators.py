"""for_each per-item action execution (spec D27): map semantics, chaining,
failure policies, caps, and publish validation."""

import uuid

import pytest

from core.models import AppliedControl, Incident
from iam.models import Folder
from workflows.actions import validate_iteration_config
from workflows.engine import start_instance
from workflows.graph import save_graph
from workflows.models import Workflow, WorkflowInstance, WorkflowNode, WorkflowVersion


def node(type_, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(source, target, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "source": source["id"],
        "target": target["id"],
        **kwargs,
    }


def make_domain(name):
    return Folder.objects.create(
        name=name,
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def chain_flow(folder, action_configs, variables=None, input_mapping=None):
    """trigger -> action(s) -> end, one node per given action_config."""
    workflow = Workflow.objects.create(name=f"Loop flow {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow)
    nodes = [
        node(
            "trigger",
            trigger_config={"type": "manual"},
            input_mapping=input_mapping or {},
        )
    ]
    for index, config in enumerate(action_configs):
        nodes.append(node("action", label=f"Step {index}", action_config=config))
    nodes.append(node("end"))
    edges = [edge(a, b) for a, b in zip(nodes, nodes[1:])]
    save_graph(
        version,
        {"nodes": nodes, "edges": edges, "variables": variables or []},
    )
    return version


def items_variable():
    return [{"id": str(uuid.uuid4()), "key": "items", "type": "string"}]


@pytest.mark.django_db
class TestForEach:
    def test_maps_over_read_results(self):
        domain = make_domain("Loop domain")
        for name in ("AC one", "AC two"):
            AppliedControl.objects.create(name=name, folder=domain)
        version = chain_flow(
            domain,
            [
                {
                    "type": "read_objects",
                    "model": "applied_control",
                    "mode": "list",
                    "order_by": "name",
                },
                {
                    "type": "log",
                    "for_each": "{{nodes.step_0.results}}",
                    "message": "#{{index}}: {{item.name}}",
                },
            ],
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = instance.node_outputs["step_1"]
        assert output["count"] == 2
        assert {r["message"] for r in output["results"]} == {
            "#0: AC one",
            "#1: AC two",
        }
        assert output["errors"] == []
        summary = instance.logs.filter(event_type="action_executed").last()
        assert "processed 2 items" in summary.message

    def test_chained_maps(self):
        domain = make_domain("Chain domain")
        AppliedControl.objects.create(name="AC", folder=domain)
        version = chain_flow(
            domain,
            [
                {"type": "read_objects", "model": "applied_control", "mode": "list"},
                {
                    "type": "log",
                    "for_each": "{{nodes.step_0.results}}",
                    "message": "notified {{item.name}}",
                },
                {
                    "type": "log",
                    "for_each": "{{nodes.step_1.results}}",
                    "message": "forwarded: {{item.message}}",
                },
            ],
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = instance.node_outputs["step_2"]
        assert output["results"] == [{"message": "forwarded: notified AC"}]

    def test_continue_policy_collects_errors_and_completes(self):
        domain = make_domain("Continue domain")
        version = chain_flow(
            domain,
            [
                {
                    "type": "create_object",
                    "model": "incident",
                    "for_each": "{{items}}",
                    "fields": {"name": "{{item.name}}"},
                }
            ],
            variables=items_variable(),
            input_mapping={"items": "items"},
        )
        instance = start_instance(
            version,
            payload={"items": [{"name": "Inc A"}, {}, {"name": "Inc B"}]},
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = instance.node_outputs["step_0"]
        assert output["count"] == 3
        assert len(output["results"]) == 2
        assert [e["index"] for e in output["errors"]] == [1]
        assert Incident.objects.filter(folder=domain).count() == 2
        summary = instance.logs.filter(event_type="action_executed").last()
        assert "1 failed" in summary.message

    def test_stop_policy_parks_the_token(self):
        domain = make_domain("Stop domain")
        version = chain_flow(
            domain,
            [
                {
                    "type": "create_object",
                    "model": "incident",
                    "for_each": "{{items}}",
                    "on_item_error": "stop",
                    "fields": {"name": "{{item.name}}"},
                }
            ],
            variables=items_variable(),
            input_mapping={"items": "items"},
        )
        instance = start_instance(
            version,
            payload={"items": [{"name": "Inc A"}, {}, {"name": "Inc B"}]},
        )
        assert instance.status != WorkflowInstance.Status.COMPLETED
        assert any(
            "item 1" in (log.message or "")
            for log in instance.logs.filter(event_type="error")
        )

    def test_zero_items_completes(self):
        domain = make_domain("Empty domain")
        version = chain_flow(
            domain,
            [
                {"type": "read_objects", "model": "applied_control", "mode": "list"},
                {
                    "type": "log",
                    "for_each": "{{nodes.step_0.results}}",
                    "message": "{{item.name}}",
                },
            ],
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert instance.node_outputs["step_1"] == {
            "count": 0,
            "results": [],
            "errors": [],
        }

    def test_non_list_resolution_is_an_error(self):
        domain = make_domain("Nonlist domain")
        version = chain_flow(
            domain,
            [
                {"type": "read_objects", "model": "applied_control", "mode": "list"},
                {
                    "type": "log",
                    "for_each": "{{nodes.step_0.count}}",
                    "message": "x",
                },
            ],
        )
        instance = start_instance(version)
        assert instance.status != WorkflowInstance.Status.COMPLETED
        assert any(
            "did not resolve to a list" in (log.message or "")
            for log in instance.logs.filter(event_type="error")
        )

    def test_item_cap(self):
        domain = make_domain("Cap domain")
        version = chain_flow(
            domain,
            [{"type": "log", "for_each": "{{items}}", "message": "{{item}}"}],
            variables=items_variable(),
            input_mapping={"items": "items"},
        )
        instance = start_instance(version, payload={"items": list(range(101))})
        assert instance.status != WorkflowInstance.Status.COMPLETED
        assert any(
            "exceeds the 100 cap" in (log.message or "")
            for log in instance.logs.filter(event_type="error")
        )

    def test_item_shadows_same_named_variable(self):
        domain = make_domain("Shadow domain")
        version = chain_flow(
            domain,
            [{"type": "log", "for_each": "{{items}}", "message": "{{item}}"}],
            variables=items_variable()
            + [{"id": str(uuid.uuid4()), "key": "item", "type": "string"}],
            input_mapping={"items": "items", "item": "decoy"},
        )
        instance = start_instance(
            version, payload={"items": ["loop-value"], "decoy": "variable-value"}
        )
        output = instance.node_outputs["step_0"]
        assert output["results"] == [{"message": "loop-value"}]
        # outside the loop the variable is intact
        assert instance.variables["item"] == "variable-value"


@pytest.mark.django_db
class TestForEachValidation:
    def _codes(self, config):
        domain = make_domain(f"Val domain {uuid.uuid4()}")
        version = chain_flow(domain, [config])
        action = version.nodes.get(type=WorkflowNode.Type.ACTION)
        return [code for code, _message in validate_iteration_config(action)]

    def test_valid_config(self):
        assert (
            self._codes(
                {
                    "type": "log",
                    "for_each": "{{nodes.a.results}}",
                    "on_item_error": "stop",
                    "message": "x",
                }
            )
            == []
        )

    def test_absent_for_each_is_fine(self):
        assert self._codes({"type": "log", "message": "x"}) == []

    def test_bare_path_rejected(self):
        assert self._codes({"type": "log", "for_each": "node.a.results"}) == [
            "for_each_invalid"
        ]

    def test_multi_template_rejected(self):
        assert self._codes({"type": "log", "for_each": "{{a}}{{b}}"}) == [
            "for_each_invalid"
        ]

    def test_bad_policy_rejected(self):
        assert self._codes(
            {"type": "log", "for_each": "{{a}}", "on_item_error": "retry"}
        ) == ["for_each_invalid"]
