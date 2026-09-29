"""The compute action: CEL arithmetic over variables and node outputs."""

import uuid

import pytest

from iam.models import Folder
from automation.workflows.actions import validate_compute_config
from automation.workflows.engine import start_instance
from automation.workflows.expressions import (
    ExpressionError,
    evaluate,
    referenced_paths,
)
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


class TestEvaluate:
    """The evaluator on its own: types in, JSON-shaped values out."""

    def test_int_arithmetic_stays_int(self):
        assert evaluate("(a + b) * 2", {"a": 3, "b": 4}) == 14
        assert isinstance(evaluate("a / 2", {"a": 7}), int)

    def test_mixing_int_and_double_promotes_to_double(self):
        # A `number` variable does not say int or double; the payload decides.
        context = {"count": 3, "weight": 2.5}
        assert evaluate("count * weight", context) == 7.5
        assert evaluate("weight + count > 5", context) is True
        assert evaluate("count == 3.0", context) is True
        # Promoted comparisons still feed CEL's own logic and ternary.
        assert evaluate("count > weight ? 'more' : 'less'", context) == "more"
        assert evaluate("count < weight || count == 3.0", context) is True
        assert evaluate("double(count) * weight", context) == 7.5
        # All-int expressions keep CEL's int semantics, so indexes still work.
        assert evaluate("[9, 8][count - 2]", context) == 8
        with pytest.raises(ExpressionError, match="cannot combine int and string"):
            evaluate("count + 'x'", context)

    def test_dotted_paths_reach_node_outputs_and_lists(self):
        context = {"nodes": {"fetch": {"count": 7, "results": [{"score": 3}]}}}
        assert evaluate("nodes.fetch.count * 2", context) == 14
        assert evaluate("nodes.fetch.results[0].score", context) == 3

    def test_aggregates_over_lists(self):
        rows = {"rows": [{"score": 3}, {"score": 5}], "empty": []}
        assert evaluate("sum(rows.map(r, r.score))", rows) == 8
        assert evaluate("avg(rows.map(r, r.score))", rows) == 4.0
        assert evaluate("max(rows.map(r, r.score))", rows) == 5
        assert evaluate("min(rows.map(r, r.score))", rows) == 3
        assert evaluate("size(rows)", rows) == 2
        assert evaluate("sum(empty)", rows) == 0
        with pytest.raises(ExpressionError, match="empty list"):
            evaluate("avg(empty)", rows)
        assert evaluate("sum([1, 2.5])", {}) == 3.5
        assert evaluate("max([1, 2.5])", {}) == 2.5

    def test_min_and_max_over_strings_and_timestamps(self):
        dates = {"dates": ["2026-03-01", "2026-01-15"]}
        assert evaluate("max(dates)", dates) == "2026-03-01"
        assert evaluate("min(dates)", dates) == "2026-01-15"
        assert (
            evaluate("max(dates.map(d, timestamp(d + 'T00:00:00Z')))", dates)
            == "2026-03-01T00:00:00+00:00"
        )
        with pytest.raises(ExpressionError, match="one kind"):
            evaluate("max(['a', 1])", {})
        with pytest.raises(ExpressionError, match="takes a list of numbers"):
            evaluate("sum(['a', 'b'])", {})

    def test_rounding_helpers(self):
        assert evaluate("round(2.567, 2)", {}) == 2.57
        assert evaluate("round(2.5)", {}) == 2
        assert evaluate("floor(2.7)", {}) == 2
        assert evaluate("ceil(2.1)", {}) == 3
        assert evaluate("abs(-3)", {}) == 3
        assert evaluate("abs(-2.5)", {}) == 2.5

    def test_conditionals_and_strings(self):
        context = {"severity": "critical", "n": 3}
        assert evaluate("severity == 'critical' ? 1 : 30", context) == 1
        assert evaluate("string(n) + ' items'", context) == "3 items"
        assert evaluate("n > 2 && severity != 'low'", context) is True

    def test_null_is_a_value(self):
        assert evaluate("missing == null", {"missing": None}) is True
        assert evaluate("has(m.x) ? m.x : 0", {"m": {}}) == 0

    def test_runtime_failures_are_named(self):
        with pytest.raises(ExpressionError, match="division by zero"):
            evaluate("1 / n", {"n": 0})
        with pytest.raises(ExpressionError, match="not a variable"):
            evaluate("unknown + 1", {})
        with pytest.raises(ExpressionError, match="no field 'x'"):
            evaluate("m.x", {"m": {}})
        with pytest.raises(ExpressionError, match="integer overflow"):
            evaluate("9223372036854775807 + 1", {})
        with pytest.raises(ExpressionError, match="syntax error"):
            evaluate("1 +", {})
        with pytest.raises(ExpressionError, match="empty"):
            evaluate("  ", {})

    def test_results_are_json_shaped(self):
        assert evaluate("[1, 2]", {}) == [1, 2]
        assert evaluate("{'a': 1}", {}) == {"a": 1}
        assert evaluate("timestamp('2026-01-01T00:00:00Z') + duration('72h')", {}) == (
            "2026-01-04T00:00:00+00:00"
        )


class TestReferencedPaths:
    def test_paths_and_prefixes_without_function_names_or_literals(self):
        paths = referenced_paths(
            "nodes.fetch.count * weight + size(rows) + 'nodes.fake.z' + double(n)"
        )
        assert {"nodes.fetch.count", "weight", "rows", "n"} <= paths
        assert "size" not in paths and "double" not in paths
        assert "nodes.fake.z" not in paths and "nodes.fake" not in paths

    def test_unparsable_expression_references_nothing(self):
        assert referenced_paths("a +") == set()


@pytest.mark.django_db
class TestComputeAction:
    def test_writes_variables_and_node_output(self):
        version = flow(
            [
                {
                    "label": "Score",
                    "type": "compute",
                    "expressions": {
                        "score": "likelihood * impact",
                        "label": "score > 12 ? 'high' : 'low'",
                    },
                }
            ],
            variables=[var("likelihood", default=4), var("impact", default=4)],
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert instance.variables["score"] == 16
        assert instance.variables["label"] == "high"
        assert instance.node_outputs["score"] == {"score": 16, "label": "high"}

    def test_entries_see_the_ones_before_them(self):
        version = flow(
            [
                {
                    "label": "Ratio",
                    "type": "compute",
                    "expressions": {
                        "ratio": "double(done) / double(total)",
                        "percent": "round(ratio * 100.0, 1)",
                    },
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
                    "expressions": {"length": "size(nodes.note.message)"},
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
                    "expressions": {
                        "sla_days": "payload.severity == 'critical' ? 1 : 30"
                    },
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
                "expressions": {"total": "total + item", "seen": "index + 1"},
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
                    "expressions": {"x": "count * label"},
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
                    "expressions": {"weighted": "count * weight"},
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
                    "expressions": {"ratio": "done / total"},
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
            [{"label": "Spoof", "type": "compute", "expressions": {"today": "'1999'"}}]
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
                    {"type": "compute", "expressions": {"x": "a + 1", "y": "x * 2"}}
                )
            )
            == []
        )

    def test_an_empty_step_is_caught(self):
        assert self.codes(
            validate_compute_config(self._node({"type": "compute", "expressions": {}}))
        ) == {"action_compute_empty"}
        assert self.codes(validate_compute_config(self._node({"type": "compute"}))) == {
            "action_compute_empty"
        }

    def test_syntax_errors_are_caught_at_publish(self):
        errors = validate_compute_config(
            self._node({"type": "compute", "expressions": {"x": "a +", "y": ""}})
        )
        assert self.codes(errors) == {"action_compute_bad_expression"}
        assert len(errors) == 2

    def test_bad_and_reserved_keys_are_caught(self):
        assert self.codes(
            validate_compute_config(
                self._node(
                    {
                        "type": "compute",
                        "expressions": {"today": "1", "9x": "1", "ok": "1"},
                    }
                )
            )
        ) == {"action_compute_reserved", "action_compute_bad_key"}

    def test_output_mapping_must_name_a_computed_key(self):
        assert self.codes(
            validate_compute_config(
                self._node(
                    {"type": "compute", "expressions": {"x": "1"}},
                    output_mapping={"y": "z"},
                )
            )
        ) == {"action_compute_unmapped_output"}

    def test_type_errors_are_a_runtime_matter(self):
        # 3 * 'x' only fails once evaluated; publish cannot know the types.
        assert (
            validate_compute_config(
                self._node({"type": "compute", "expressions": {"x": "count * label"}})
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
                    "expressions": {"n": "nodes.missing.count + 1"},
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
                    "expressions": {"n": "size(nodes.note.message)"},
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
            action_config={"type": "compute", "expressions": {"derived": expression}},
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
