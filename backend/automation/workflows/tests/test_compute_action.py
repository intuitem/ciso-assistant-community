"""The compute action: CEL arithmetic over variables and node outputs."""

import uuid

import pytest

from iam.models import Folder
from automation.workflows.actions import validate_compute_config
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowInstanceLog,
    WorkflowNode,
    WorkflowVersion,
)
from automation.workflows.validation import validate_graph
from automation.workflows.tests.helpers import publisher_user
from automation.workflows.tests.test_ai_actions import SEVERITY_SCHEMA


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


def flow(action_configs, variables=None, input_mapping=None):
    """Manual trigger -> the given action nodes in sequence -> end."""
    workflow = Workflow.objects.create(
        name=f"Compute flow {uuid.uuid4()}", folder=Folder.get_root_folder()
    )
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node(
        "trigger", trigger_config={"type": "manual"}, input_mapping=input_mapping or {}
    )
    steps = [
        node(
            "action",
            label=config.pop("label", "step"),
            ref=config.pop("ref", None),
            action_config=config,
        )
        for config in action_configs
    ]
    end = node("end")
    chain = [start, *steps, end]
    save_graph(
        version,
        {
            "nodes": chain,
            "edges": [edge(a, b) for a, b in zip(chain, chain[1:])],
            "variables": [
                {"id": str(uuid.uuid4()), **variable} for variable in (variables or [])
            ],
        },
    )
    return version


def var(key, type_="number", default=None):
    return {"key": key, "type": type_, "default_value": default}


def error_messages(instance):
    return [
        log.message
        for log in instance.logs.filter(event_type=WorkflowInstanceLog.EventType.ERROR)
    ]


@pytest.mark.django_db
class TestComputeAction:
    def test_writes_variables_and_node_output(self):
        # `label` reads `score`, and sorts before it: PostgreSQL's jsonb
        # reorders object keys, which is why rows are a list and not a dict.
        version = flow(
            [
                {
                    "label": "Score",
                    "type": "compute",
                    "expressions": [
                        {"key": "score", "expression": "likelihood * impact"},
                        {"key": "label", "expression": "score > 12 ? 'high' : 'low'"},
                    ],
                }
            ],
            variables=[var("likelihood", default=4), var("impact", default=4)],
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, error_messages(
            instance
        )
        assert instance.variables["score"] == 16
        assert instance.variables["label"] == "high"
        assert instance.node_outputs["score"] == {"score": 16, "label": "high"}

    def test_entries_see_the_ones_before_them(self):
        version = flow(
            [
                {
                    "label": "Ratio",
                    "type": "compute",
                    "expressions": [
                        {"key": "ratio", "expression": "double(done) / double(total)"},
                        {"key": "percent", "expression": "round(ratio * 100.0, 1)"},
                    ],
                }
            ],
            variables=[var("done", default=1), var("total", default=3)],
        )
        instance = start_instance(version)
        assert instance.variables["percent"] == 33.3

    def test_reads_an_earlier_node_output(self):
        version = flow(
            [
                {
                    "label": "Note",
                    "ref": "note",
                    "type": "log",
                    "message": "hello",
                },
                {
                    "label": "Length",
                    "type": "compute",
                    "expressions": [
                        {"key": "length", "expression": "size(nodes.note.message)"}
                    ],
                },
            ],
        )
        instance = start_instance(version)
        assert instance.variables["length"] == 5

    def test_reads_the_payload(self):
        version = flow(
            [
                {
                    "label": "Due",
                    "type": "compute",
                    "expressions": [
                        {
                            "key": "sla_days",
                            "expression": "payload.severity == 'critical' ? 1 : 30",
                        }
                    ],
                }
            ],
        )
        instance = start_instance(version, payload={"severity": "critical"})
        assert instance.variables["sla_days"] == 1

    def test_accumulates_inside_a_loop(self):
        workflow = Workflow.objects.create(
            name="Loop sum", folder=Folder.get_root_folder()
        )
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        start = node("trigger", trigger_config={"type": "manual"})
        loop = node(
            "loop",
            label="Each",
            loop_config={"collection": "{{payload.scores}}"},
        )
        add = node(
            "action",
            label="Add",
            action_config={
                "type": "compute",
                "expressions": [
                    {"key": "total", "expression": "total + item"},
                    {"key": "seen", "expression": "index + 1"},
                ],
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, loop, add, end],
                "edges": [
                    edge(start, loop),
                    edge(loop, add, source_port="each"),
                    edge(add, loop),
                    edge(loop, end, source_port="done"),
                ],
                "variables": [
                    {"id": str(uuid.uuid4()), **var("total", default=0)},
                    {"id": str(uuid.uuid4()), **var("seen", default=0)},
                ],
            },
        )
        instance = start_instance(version, payload={"scores": [2, 3, 5]})
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert instance.variables["total"] == 10
        assert instance.variables["seen"] == 3

    def test_a_type_error_fails_the_node_without_retrying(self):
        version = flow(
            [
                {
                    "label": "Bad",
                    "type": "compute",
                    "expressions": [{"key": "x", "expression": "count * label"}],
                }
            ],
            variables=[var("count", default=3), var("label", "string", "high")],
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any(
            "cannot combine int and string" in message
            for message in error_messages(instance)
        )

    def test_int_and_double_variables_mix(self):
        version = flow(
            [
                {
                    "label": "Weighted",
                    "type": "compute",
                    "expressions": [
                        {"key": "weighted", "expression": "count * weight"}
                    ],
                }
            ],
            variables=[var("count", default=3), var("weight", default=2.5)],
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert instance.variables["weighted"] == 7.5

    def test_division_by_zero_fails_the_node(self):
        version = flow(
            [
                {
                    "label": "Ratio",
                    "type": "compute",
                    "expressions": [{"key": "ratio", "expression": "done / total"}],
                }
            ],
            variables=[var("done", default=1), var("total", default=0)],
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any(
            "division by zero" in message for message in error_messages(instance)
        )

    def test_reserved_keys_are_refused_at_runtime(self):
        version = flow(
            [
                {
                    "label": "Spoof",
                    "type": "compute",
                    "expressions": [{"key": "today", "expression": "'1999'"}],
                }
            ]
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert instance.variables["today"] != "1999"


class TestComputeValidation:
    def _node(self, config, **kwargs):
        return WorkflowNode(action_config=config, **kwargs)

    def codes(self, errors):
        return {code for code, _ in errors}

    def test_a_clean_config_passes(self):
        assert (
            validate_compute_config(
                self._node(
                    {
                        "type": "compute",
                        "expressions": [
                            {"key": "x", "expression": "a + 1"},
                            {"key": "y", "expression": "x * 2"},
                        ],
                    }
                )
            )
            == []
        )

    def test_an_empty_step_is_caught(self):
        assert self.codes(
            validate_compute_config(self._node({"type": "compute", "expressions": []}))
        ) == {"action_compute_empty"}
        assert self.codes(validate_compute_config(self._node({"type": "compute"}))) == {
            "action_compute_empty"
        }

    def test_syntax_errors_are_caught_at_publish(self):
        errors = validate_compute_config(
            self._node(
                {
                    "type": "compute",
                    "expressions": [
                        {"key": "x", "expression": "a +"},
                        {"key": "y", "expression": ""},
                    ],
                }
            )
        )
        assert self.codes(errors) == {"action_compute_bad_expression"}
        assert len(errors) == 2

    def test_bad_and_reserved_keys_are_caught(self):
        assert self.codes(
            validate_compute_config(
                self._node(
                    {
                        "type": "compute",
                        "expressions": [
                            {"key": "today", "expression": "1"},
                            {"key": "9x", "expression": "1"},
                            {"key": "ok", "expression": "1"},
                        ],
                    }
                )
            )
        ) == {"action_compute_reserved", "action_compute_bad_key"}

    def test_duplicate_keys_are_caught(self):
        assert self.codes(
            validate_compute_config(
                self._node(
                    {
                        "type": "compute",
                        "expressions": [
                            {"key": "x", "expression": "1"},
                            {"key": "x", "expression": "2"},
                        ],
                    }
                )
            )
        ) == {"action_compute_duplicate_key"}

    def test_a_dict_shaped_config_is_treated_as_empty(self):
        # The shape an early draft used; jsonb would reorder it.
        assert self.codes(
            validate_compute_config(
                self._node({"type": "compute", "expressions": {"x": "1"}})
            )
        ) == {"action_compute_empty"}

    def test_a_row_that_is_not_a_row_is_refused(self):
        expressions = [{"key": "x", "expression": "1"}, "y = 2"]
        assert self.codes(
            validate_compute_config(
                self._node({"type": "compute", "expressions": expressions})
            )
        ) == {"action_compute_malformed"}

    def test_output_mapping_must_name_a_computed_key(self):
        assert self.codes(
            validate_compute_config(
                self._node(
                    {
                        "type": "compute",
                        "expressions": [{"key": "x", "expression": "1"}],
                    },
                    output_mapping={"y": "z"},
                )
            )
        ) == {"action_compute_unmapped_output"}

    def test_type_errors_are_a_runtime_matter(self):
        # 3 * 'x' only fails once evaluated; publish cannot know the types.
        assert (
            validate_compute_config(
                self._node(
                    {
                        "type": "compute",
                        "expressions": [{"key": "x", "expression": "count * label"}],
                    }
                )
            )
            == []
        )


@pytest.mark.django_db
class TestComputeGraphValidation:
    def test_an_unknown_node_ref_in_an_expression_is_caught(self):
        version = flow(
            [
                {
                    "label": "Length",
                    "type": "compute",
                    "expressions": [
                        {"key": "n", "expression": "nodes.missing.count + 1"}
                    ],
                }
            ],
            variables=[var("n")],
        )
        codes = {error["code"] for error in validate_graph(version)}
        assert "node_reference_missing" in codes

    def test_a_known_node_ref_passes(self):
        version = flow(
            [
                {"label": "Note", "ref": "note", "type": "log", "message": "x"},
                {
                    "label": "Length",
                    "type": "compute",
                    "expressions": [
                        {"key": "n", "expression": "size(nodes.note.message)"}
                    ],
                },
            ],
            variables=[var("n")],
        )
        codes = {error["code"] for error in validate_graph(version)}
        assert "node_reference_missing" not in codes


@pytest.mark.django_db
class TestAiProvenanceThroughCompute:
    """A number derived from a model's answer is still a model's answer:
    routing it through compute must not walk it past the fence."""

    def graph(self, expression, target_field="severity"):
        workflow = Workflow.objects.create(
            name="Launder", folder=Folder.get_root_folder()
        )
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        start = node("trigger", trigger_config={"type": "manual"})
        classify = node(
            "action",
            ref="classify",
            action_config={
                "type": "ai_extract",
                "prompt": "Classify",
                "schema": SEVERITY_SCHEMA,
            },
            output_mapping={"ai_severity": "severity"},
        )
        hop = node(
            "action",
            ref="hop",
            action_config={
                "type": "compute",
                "expressions": [{"key": "derived", "expression": expression}],
            },
        )
        write = node(
            "action",
            ref="write",
            action_config={
                "type": "update_object",
                "model": "finding",
                "id": "{{finding_id}}",
                "fields": {target_field: "{{derived}}"},
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, hop, classify, write, end],
                "edges": [
                    edge(start, classify),
                    edge(classify, hop),
                    edge(hop, write),
                    edge(write, end),
                ],
                "variables": [
                    {"id": str(uuid.uuid4()), "key": key, "type": "string"}
                    for key in ["finding_id", "ai_severity", "derived"]
                ],
            },
        )
        return version

    def codes(self, version):
        return {error["code"] for error in validate_graph(version)}

    def test_a_variable_hop_is_refused(self):
        assert "action_update_ai_value_on_fenced_field" in self.codes(
            self.graph("ai_severity == 'high' ? 'critical' : 'low'")
        )

    def test_a_node_reference_hop_is_refused(self):
        assert "action_update_ai_value_on_fenced_field" in self.codes(
            self.graph("nodes.classify.severity")
        )

    def test_an_unrelated_expression_is_not_tainted(self):
        assert "action_update_ai_value_on_fenced_field" not in self.codes(
            self.graph("'high'")
        )


@pytest.mark.django_db
class TestAiProvenanceEscapes:
    """Ways a compute row could carry an AI answer past the fence that plain
    `.field` tracking missed."""

    def graph(
        self, expression, output_mapping=None, write="{{derived}}", extra_rows=()
    ):
        workflow = Workflow.objects.create(
            name="Escape", folder=Folder.get_root_folder()
        )
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        start = node("trigger", trigger_config={"type": "manual"})
        classify = node(
            "action",
            ref="classify",
            action_config={
                "type": "ai_extract",
                "prompt": "Classify",
                "schema": SEVERITY_SCHEMA,
            },
            output_mapping={"ai_severity": "severity"},
        )
        hop = node(
            "action",
            ref="hop",
            action_config={
                "type": "compute",
                "expressions": [
                    {"key": "derived", "expression": expression},
                    *extra_rows,
                ],
            },
            output_mapping=output_mapping or {},
        )
        update = node(
            "action",
            ref="write",
            action_config={
                "type": "update_object",
                "model": "finding",
                "id": "{{finding_id}}",
                "fields": {"severity": write},
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, classify, hop, update, end],
                "edges": [
                    edge(start, classify),
                    edge(classify, hop),
                    edge(hop, update),
                    edge(update, end),
                ],
                "variables": [
                    {"id": str(uuid.uuid4()), "key": key, "type": "string"}
                    for key in [
                        "finding_id",
                        "ai_severity",
                        "derived",
                        "alias",
                        "fixed",
                    ]
                ],
            },
        )
        return {error["code"] for error in validate_graph(version)}

    def test_index_access_to_the_ai_step_is_fenced(self):
        assert "action_update_ai_value_on_fenced_field" in self.graph(
            "nodes['classify']['severity']"
        )

    def test_a_computed_index_over_nodes_is_fenced(self):
        assert "action_update_ai_value_on_fenced_field" in self.graph(
            "nodes[key].severity"
        )

    def test_an_output_mapping_alias_of_a_tainted_row_is_fenced(self):
        assert "action_update_ai_value_on_fenced_field" in self.graph(
            "nodes.classify.severity",
            output_mapping={"alias": "derived"},
            write="{{alias}}",
        )

    def test_the_compute_steps_own_output_is_fenced(self):
        assert "action_update_ai_value_on_fenced_field" in self.graph(
            "nodes.classify.severity", write="{{nodes.hop.derived}}"
        )

    def test_an_untainted_step_output_is_not(self):
        assert "action_update_ai_value_on_fenced_field" not in self.graph(
            "'high'", write="{{nodes.hop.derived}}"
        )

    def test_an_escaped_index_is_fenced(self):
        # CEL decodes it to 'classify'; its raw text is not the ref.
        assert "action_update_ai_value_on_fenced_field" in self.graph(
            "nodes['cl\\x61ssify']['severity']"
        )

    def test_a_triple_quoted_index_is_fenced(self):
        assert "action_update_ai_value_on_fenced_field" in self.graph(
            "nodes['''classify''']['severity']"
        )

    def test_a_clean_sibling_row_of_a_tainted_one_is_not(self):
        assert "action_update_ai_value_on_fenced_field" not in self.graph(
            "nodes.classify.severity",
            write="{{nodes.hop.fixed}}",
            extra_rows=[{"key": "fixed", "expression": "'high'"}],
        )

    def test_the_whole_output_of_a_partly_tainted_step_is_fenced(self):
        assert "action_update_ai_value_on_fenced_field" in self.graph(
            "nodes.classify.severity",
            write="{{nodes.hop}}",
            extra_rows=[{"key": "fixed", "expression": "'high'"}],
        )
