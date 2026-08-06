"""Loop node (spec D29): controller/body token semantics, multi-step bodies,
in-body conditions on {{item}}, failure policies, caps, nesting, validation."""

import uuid

import pytest

from core.models import AppliedControl, Incident
from iam.models import Folder
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import Workflow, WorkflowInstance, WorkflowVersion
from automation.workflows.validation import validate_graph
from automation.workflows.tests.helpers import publisher_user


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


def loop_flow(folder, loop_config, body_configs, variables=None, input_mapping=None):
    """trigger -> loop( each -> body chain -> back ) -> done -> end."""
    workflow = Workflow.objects.create(name=f"Loop flow {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    trigger = node(
        "trigger",
        trigger_config={"type": "manual"},
        input_mapping=input_mapping or {},
    )
    loop = node("loop", label="Per item", loop_config=loop_config)
    body = [
        node("action", label=f"Body {i}", action_config=config)
        for i, config in enumerate(body_configs)
    ]
    end = node("end")
    edges = [edge(trigger, loop)]
    chain = [loop, *body]
    edges.append(edge(loop, body[0], source_port="each"))
    for a, b in zip(body, body[1:]):
        edges.append(edge(a, b))
    edges.append(edge(body[-1], loop))
    edges.append(edge(loop, end, source_port="done"))
    save_graph(
        version,
        {
            "nodes": [trigger, *chain, end],
            "edges": edges,
            "variables": variables or [],
        },
    )
    return version


def items_variable():
    return [{"id": str(uuid.uuid4()), "key": "items", "type": "string"}]


@pytest.mark.django_db
class TestLoopNode:
    def test_multi_step_body_runs_per_item(self):
        domain = make_domain("Loop domain")
        version = loop_flow(
            domain,
            {"collection": "{{items}}", "collect": "{{nodes.body_1.message}}"},
            [
                {"type": "log", "message": "first {{item}}"},
                {"type": "log", "message": "second {{item}} #{{index}}"},
            ],
            variables=items_variable(),
            input_mapping={"items": "items"},
        )
        instance = start_instance(version, payload={"items": ["a", "b"]})
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = instance.node_outputs["per_item"]
        assert output["count"] == 2
        assert output["results"] == ["second a #0", "second b #1"]
        assert output["errors"] == []
        summary = instance.logs.filter(event_type="loop_completed").last()
        assert "processed 2 items" in summary.message

    def test_loop_over_read_results(self):
        domain = make_domain("Read loop domain")
        for name in ("AC one", "AC two"):
            AppliedControl.objects.create(name=name, folder=domain)
        workflow = Workflow.objects.create(name="Read loop", folder=domain)
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        trigger = node("trigger", trigger_config={"type": "manual"})
        read = node(
            "action",
            label="List controls",
            action_config={
                "type": "read_objects",
                "model": "applied_control",
                "mode": "list",
                "order_by": "name",
            },
        )
        loop = node(
            "loop",
            label="Notify each",
            loop_config={
                "collection": "{{nodes.list_controls.results}}",
                "collect": "{{nodes.notify.message}}",
            },
        )
        notify = node(
            "action",
            label="Notify",
            action_config={"type": "log", "message": "reminder: {{item.name}}"},
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [trigger, read, loop, notify, end],
                "edges": [
                    edge(trigger, read),
                    edge(read, loop),
                    edge(loop, notify, source_port="each"),
                    edge(notify, loop),
                    edge(loop, end, source_port="done"),
                ],
                "variables": [],
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert instance.node_outputs["notify_each"]["results"] == [
            "reminder: AC one",
            "reminder: AC two",
        ]

    def test_in_body_condition_sees_item(self):
        domain = make_domain("Branchy loop domain")
        workflow = Workflow.objects.create(name="Branchy", folder=domain)
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        var_id = str(uuid.uuid4())
        sev_id = str(uuid.uuid4())
        trigger = node(
            "trigger",
            trigger_config={"type": "manual"},
            input_mapping={"items": "items"},
        )
        loop = node(
            "loop",
            label="Route each",
            loop_config={"collection": "{{items}}"},
        )
        # set_variables maps the item into a variable; the condition compares
        # it against a templated value proving {{item.*}} works in conditions.
        stage = node(
            "action",
            label="Stage",
            action_config={
                "type": "set_variables",
                "variables": {"sev": "{{item.sev}}"},
            },
        )
        branch_high = {
            "id": str(uuid.uuid4()),
            "name": "high",
            "order": 0,
            "is_default": False,
            "condition_groups": [
                {
                    "operator": "and",
                    "order": 0,
                    "conditions": [
                        {"variable": sev_id, "op": "eq", "value": "high", "order": 0}
                    ],
                    "children": [],
                }
            ],
        }
        branch_rest = {
            "id": str(uuid.uuid4()),
            "name": "rest",
            "order": 1,
            "is_default": True,
            "condition_groups": [],
        }
        cond = node("condition", label="Sev?", branches=[branch_high, branch_rest])
        escalate = node(
            "action",
            label="Escalate",
            action_config={
                "type": "create_object",
                "model": "incident",
                "fields": {"name": "Escalation {{item.name}}"},
            },
        )
        skip = node(
            "action", label="Skip", action_config={"type": "log", "message": "-"}
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [trigger, loop, stage, cond, escalate, skip, end],
                "edges": [
                    edge(trigger, loop),
                    edge(loop, stage, source_port="each"),
                    edge(stage, cond),
                    edge(cond, escalate, source_branch=branch_high["id"]),
                    edge(cond, skip, source_branch=branch_rest["id"]),
                    edge(escalate, loop),
                    edge(skip, loop),
                    edge(loop, end, source_port="done"),
                ],
                "variables": [
                    {"id": var_id, "key": "items", "type": "string"},
                    {"id": sev_id, "key": "sev", "type": "string"},
                ],
            },
        )
        instance = start_instance(
            version,
            payload={
                "items": [
                    {"name": "one", "sev": "high"},
                    {"name": "two", "sev": "low"},
                    {"name": "three", "sev": "high"},
                ]
            },
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED
        created = set(
            Incident.objects.filter(folder=domain).values_list("name", flat=True)
        )
        assert created == {"Escalation one", "Escalation three"}

    def test_continue_policy_records_errors_and_completes(self):
        domain = make_domain("Continue domain")
        version = loop_flow(
            domain,
            {"collection": "{{items}}", "on_item_error": "continue"},
            [
                {
                    "type": "create_object",
                    "model": "incident",
                    "fields": {"name": "{{item.name}}"},
                }
            ],
            variables=items_variable(),
            input_mapping={"items": "items"},
        )
        instance = start_instance(
            version, payload={"items": [{"name": "Inc A"}, {}, {"name": "Inc B"}]}
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = instance.node_outputs["per_item"]
        assert output["count"] == 3
        assert [e["index"] for e in output["errors"]] == [1]
        assert Incident.objects.filter(folder=domain).count() == 2
        summary = instance.logs.filter(event_type="loop_completed").last()
        assert "1 failed" in summary.message

    def test_stop_policy_fails_the_run(self):
        domain = make_domain("Stop domain")
        version = loop_flow(
            domain,
            {"collection": "{{items}}", "on_item_error": "stop"},
            [
                {
                    "type": "create_object",
                    "model": "incident",
                    "fields": {"name": "{{item.name}}"},
                }
            ],
            variables=items_variable(),
            input_mapping={"items": "items"},
        )
        instance = start_instance(
            version, payload={"items": [{"name": "Inc A"}, {}, {"name": "Inc B"}]}
        )
        # Stop policy fails the controller (spec D29) — no WAITING hang, and the
        # third item is never processed.
        assert instance.status == WorkflowInstance.Status.FAILED
        from automation.workflows.models import WorkflowToken

        assert not instance.tokens.filter(status=WorkflowToken.Status.WAITING).exists()
        assert Incident.objects.filter(folder=domain).count() == 1

    def test_zero_items_completes(self):
        domain = make_domain("Empty domain")
        version = loop_flow(
            domain,
            {"collection": "{{items}}"},
            [{"type": "log", "message": "{{item}}"}],
            variables=items_variable(),
            input_mapping={"items": "items"},
        )
        instance = start_instance(version, payload={"items": []})
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert instance.node_outputs["per_item"] == {
            "count": 0,
            "results": [],
            "errors": [],
        }

    def test_non_list_collection_is_an_error(self):
        domain = make_domain("Nonlist domain")
        version = loop_flow(
            domain,
            {"collection": "{{items}}"},
            [{"type": "log", "message": "x"}],
            variables=items_variable(),
            input_mapping={"items": "items"},
        )
        instance = start_instance(version, payload={"items": "not-a-list"})
        assert instance.status != WorkflowInstance.Status.COMPLETED
        assert any(
            "did not resolve to a list" in (log.message or "")
            for log in instance.logs.filter(event_type="error")
        )

    def test_item_cap(self):
        domain = make_domain("Cap domain")
        version = loop_flow(
            domain,
            {"collection": "{{items}}"},
            [{"type": "log", "message": "{{item}}"}],
            variables=items_variable(),
            input_mapping={"items": "items"},
        )
        instance = start_instance(version, payload={"items": list(range(101))})
        assert instance.status != WorkflowInstance.Status.COMPLETED
        assert any(
            "exceeds the 100 cap" in (log.message or "")
            for log in instance.logs.filter(event_type="error")
        )

    def test_post_loop_action_does_not_clobber_loop_output(self):
        # Regression: the controller used to write its output through a
        # lazily-loaded instance copy; the next node's save then clobbered it.
        domain = make_domain("Clobber domain")
        workflow = Workflow.objects.create(name="Clobber", folder=domain)
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        trigger = node(
            "trigger",
            trigger_config={"type": "manual"},
            input_mapping={"items": "items"},
        )
        loop = node(
            "loop",
            label="Per item",
            loop_config={"collection": "{{items}}", "collect": "{{item}}"},
        )
        body = node(
            "action", label="Body", action_config={"type": "log", "message": "x"}
        )
        after = node(
            "action",
            label="After",
            action_config={"type": "log", "message": "saw {{nodes.per_item.count}}"},
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [trigger, loop, body, after, end],
                "edges": [
                    edge(trigger, loop),
                    edge(loop, body, source_port="each"),
                    edge(body, loop),
                    edge(loop, after, source_port="done"),
                    edge(after, end),
                ],
                "variables": items_variable(),
            },
        )
        instance = start_instance(version, payload={"items": ["a", "b"]})
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert instance.node_outputs["per_item"]["count"] == 2
        assert instance.node_outputs["after"]["message"] == "saw 2"

    def test_nested_loops_use_innermost_item(self):
        domain = make_domain("Nested domain")
        workflow = Workflow.objects.create(name="Nested", folder=domain)
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        trigger = node(
            "trigger",
            trigger_config={"type": "manual"},
            input_mapping={"groups": "groups"},
        )
        outer = node(
            "loop",
            label="Outer",
            loop_config={
                "collection": "{{groups}}",
                "collect": "{{nodes.inner.results}}",
            },
        )
        inner = node(
            "loop",
            label="Inner",
            loop_config={
                "collection": "{{item.members}}",
                "collect": "{{nodes.tag.message}}",
            },
        )
        tag = node(
            "action",
            label="Tag",
            action_config={"type": "log", "message": "member {{item}}"},
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [trigger, outer, inner, tag, end],
                "edges": [
                    edge(trigger, outer),
                    edge(outer, inner, source_port="each"),
                    edge(inner, tag, source_port="each"),
                    edge(tag, inner),
                    edge(inner, outer, source_port="done"),
                    edge(outer, end, source_port="done"),
                ],
                "variables": [
                    {"id": str(uuid.uuid4()), "key": "groups", "type": "string"}
                ],
            },
        )
        instance = start_instance(
            version,
            payload={"groups": [{"members": ["a", "b"]}, {"members": ["c"]}]},
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = instance.node_outputs["outer"]
        # collect resolves a single {{path}} with dig(), preserving the list
        # type instead of JSON-stringifying it (regression fix).
        assert output["results"] == [
            ["member a", "member b"],
            ["member c"],
        ]

    def test_stop_inside_an_inner_loop_kills_both_controllers(self):
        """Terminating from the innermost body consumes every parked controller,
        so neither loop resumes (spec D35)."""
        domain = make_domain("Nested stop domain")
        workflow = Workflow.objects.create(name="Nested stop", folder=domain)
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        trigger = node(
            "trigger",
            trigger_config={"type": "manual"},
            input_mapping={"groups": "groups"},
        )
        outer = node("loop", label="Outer", loop_config={"collection": "{{groups}}"})
        inner = node(
            "loop", label="Inner", loop_config={"collection": "{{item.members}}"}
        )
        halt = node("end", label="Stop")
        after = node("action", label="After", action_config={"type": "log"})
        save_graph(
            version,
            {
                "nodes": [trigger, outer, inner, halt, after],
                "edges": [
                    edge(trigger, outer),
                    edge(outer, inner, source_port="each"),
                    # First item of the first group stops the whole run.
                    edge(inner, halt, source_port="each"),
                    edge(inner, outer, source_port="done"),
                    edge(outer, after, source_port="done"),
                ],
                "variables": [
                    {"id": str(uuid.uuid4()), "key": "groups", "type": "string"}
                ],
            },
        )
        instance = start_instance(
            version,
            payload={"groups": [{"members": ["a", "b"]}, {"members": ["c"]}]},
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED
        from automation.workflows.models import WorkflowToken

        assert not instance.tokens.filter(
            status__in=[
                WorkflowToken.Status.ACTIVE,
                WorkflowToken.Status.WAITING,
                WorkflowToken.Status.RETRYING,
            ]
        ).exists()
        # Neither loop reached its done port.
        assert not instance.logs.filter(
            event_type="node_entered", node__label="After"
        ).exists()
        assert not instance.logs.filter(event_type="loop_completed").exists()
        assert instance.logs.filter(event_type="run_terminated").count() == 1


@pytest.mark.django_db
class TestLoopValidation:
    def _codes(self, mutate):
        domain = make_domain(f"Val domain {uuid.uuid4()}")
        version = loop_flow(
            domain,
            {"collection": "{{items}}"},
            [{"type": "log", "message": "x"}],
            variables=items_variable(),
            input_mapping={"items": "items"},
        )
        mutate(version)
        return [e["code"] for e in validate_graph(version)]

    def test_valid_loop_passes(self):
        codes = self._codes(lambda version: None)
        assert not any(code.startswith("loop") for code in codes)
        # A loop is a legitimate cycle: the back edge must not read as a graph
        # that can never finish (guards the leaf-based dead_end rule, spec D35).
        assert "dead_end" not in codes

    def test_missing_collection(self):
        def mutate(version):
            loop = version.nodes.get(type="loop")
            loop.loop_config = {}
            loop.save(update_fields=["loop_config"])

        assert "loop_collection_invalid" in self._codes(mutate)

    def test_body_without_return(self):
        def mutate(version):
            loop = version.nodes.get(type="loop")
            version.edges.filter(target_node=loop).exclude(
                source_node__type="trigger"
            ).delete()

        codes = self._codes(mutate)
        assert "loop_body_no_return" in codes

    def test_body_escape_to_done_side(self):
        def mutate(version):
            from automation.workflows.models import WorkflowEdge

            body = version.nodes.get(label="Body 0")
            end = version.nodes.get(type="end")
            WorkflowEdge.objects.create(
                version=version, source_node=body, target_node=end
            )

        assert "loop_body_escape" in self._codes(mutate)

    def test_own_end_node_in_body_is_not_an_escape(self):
        """Terminating from inside a loop body is legitimate (spec D35): the
        end node consumes the controller, so nothing is left waiting."""

        def mutate(version):
            from automation.workflows.models import WorkflowEdge, WorkflowNode

            body = version.nodes.get(label="Body 0")
            halt = WorkflowNode.objects.create(
                version=version, type=WorkflowNode.Type.END, label="Stop"
            )
            WorkflowEdge.objects.create(
                version=version, source_node=body, target_node=halt
            )

        codes = self._codes(mutate)
        assert "loop_body_escape" not in codes
        assert "loop_body_no_return" not in codes

    def test_source_port_on_non_loop_edge(self):
        def mutate(version):
            edge_row = version.edges.filter(source_node__type="trigger").first()
            edge_row.source_port = "each"
            edge_row.save(update_fields=["source_port"])

        assert "loop_port_missing" in self._codes(mutate)

    def test_body_fan_out_is_rejected(self):
        """Parallel fan-out inside a loop body corrupts the controller's
        per-iteration accounting, so it must be blocked at publish."""
        domain = make_domain(f"Fanout {uuid.uuid4()}")
        version = loop_flow(
            domain,
            {"collection": "{{items}}"},
            [{"type": "log", "message": "a"}, {"type": "log", "message": "b"}],
            variables=items_variable(),
            input_mapping={"items": "items"},
        )
        from automation.workflows.models import WorkflowEdge

        loop = version.nodes.get(type="loop")
        body0 = version.nodes.get(label="Body 0")
        # Body 0 now fans out to Body 1 AND straight back to the loop.
        WorkflowEdge.objects.create(
            version=version, source_node=body0, target_node=loop
        )
        codes = [e["code"] for e in validate_graph(version)]
        assert "loop_body_fan_out" in codes

    def test_condition_in_body_is_not_fan_out(self):
        """A condition node in the body fans out edges but fires only one
        branch, so it must NOT trip the fan-out guard."""
        codes = self._codes(lambda version: None)
        assert "loop_body_fan_out" not in codes
