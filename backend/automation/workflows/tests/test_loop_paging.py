"""A loop can pull its own pages, so a sweep stays three nodes whatever the
size of the set."""

import uuid

import pytest
from django.test import override_settings

from core.models import AppliedControl
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


def paging_flow(folder, loop_config):
    workflow = Workflow.objects.create(name=f"Sweep {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", trigger_config={"type": "manual"})
    loop = node("loop", label="Each row", loop_config=loop_config)
    body = node(
        "action",
        label="Note it",
        action_config={"type": "log", "message": "{{item.name}}"},
    )
    end = node("end")
    save_graph(
        version,
        {
            "nodes": [start, loop, body, end],
            "edges": [
                edge(start, loop),
                edge(loop, body, source_port="each"),
                edge(body, loop),
                edge(loop, end, source_port="done"),
            ],
        },
    )
    return version


@pytest.mark.django_db
class TestPagingLoop:
    def test_it_walks_every_page(self):
        domain = make_domain("Sweep all")
        for index in range(7):
            AppliedControl.objects.create(name=f"AC {index:02d}", folder=domain)
        version = paging_flow(
            domain,
            {
                "read": {"model": "applied_control", "order_by": "name", "limit": 3},
                "collect": "{{item.name}}",
                "on_item_error": "continue",
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        output = instance.node_outputs["each_row"]
        assert output["count"] == 7
        assert output["pages"] == 3
        assert output["results"] == [f"AC {i:02d}" for i in range(7)]

    def test_a_single_page_set_still_works(self):
        domain = make_domain("Sweep one page")
        AppliedControl.objects.create(name="Only one", folder=domain)
        version = paging_flow(
            domain,
            {
                "read": {"model": "applied_control", "limit": 25},
                "collect": "{{item.name}}",
            },
        )
        output = start_instance(version).node_outputs["each_row"]
        assert output["count"] == 1
        assert output["pages"] == 1

    def test_an_empty_set_finishes_through_done(self):
        domain = make_domain("Sweep empty")
        version = paging_flow(
            domain, {"read": {"model": "applied_control", "limit": 5}}
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert instance.node_outputs["each_row"]["count"] == 0

    @override_settings(WORKFLOW_LOOP_MAX_PAGES=2)
    def test_it_stops_at_the_page_ceiling_and_says_so(self):
        domain = make_domain("Sweep capped")
        for index in range(9):
            AppliedControl.objects.create(name=f"AC {index:02d}", folder=domain)
        version = paging_flow(
            domain,
            {"read": {"model": "applied_control", "order_by": "name", "limit": 2}},
        )
        output = start_instance(version).node_outputs["each_row"]
        assert output["pages"] == 2
        assert output["count"] == 4
        # Never silent: the run says where it stopped.
        assert any("stopped after" in e["message"] for e in output["errors"])

    def test_a_mutating_sweep_covers_the_whole_set(self):
        """The flagship sweep filters on the very field the body updates.
        Offset paging over the live queryset would skip ~limit rows per page
        as processed rows drop out of the match; the frozen id snapshot keeps
        coverage complete."""
        domain = make_domain("Sweep mutating")
        for index in range(6):
            AppliedControl.objects.create(
                name=f"AC {index:02d}", folder=domain, status="to_do"
            )
        workflow = Workflow.objects.create(name="Mutating sweep", folder=domain)
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        start = node("trigger", trigger_config={"type": "manual"})
        loop = node(
            "loop",
            label="Each row",
            loop_config={
                "read": {
                    "model": "applied_control",
                    "order_by": "name",
                    "limit": 2,
                    "filters": {
                        "operator": "and",
                        "conditions": [
                            {"field": "status", "op": "eq", "value": "to_do"}
                        ],
                    },
                },
                "collect": "{{item.name}}",
            },
        )
        body = node(
            "action",
            label="Activate",
            action_config={
                "type": "update_object",
                "model": "applied_control",
                "id": "{{item.id}}",
                "fields": {"status": "active"},
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, loop, body, end],
                "edges": [
                    edge(start, loop),
                    edge(loop, body, source_port="each"),
                    edge(body, loop),
                    edge(loop, end, source_port="done"),
                ],
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        output = instance.node_outputs["each_row"]
        assert output["count"] == 6
        assert output["results"] == [f"AC {i:02d}" for i in range(6)]
        assert not AppliedControl.objects.filter(
            folder=domain, status="to_do"
        ).exists()

    def test_the_filters_apply_to_every_page(self):
        domain = make_domain("Sweep filtered")
        for index in range(6):
            AppliedControl.objects.create(
                name=f"AC {index:02d}",
                folder=domain,
                status="active" if index % 2 else "to_do",
            )
        version = paging_flow(
            domain,
            {
                "read": {
                    "model": "applied_control",
                    "order_by": "name",
                    "limit": 2,
                    "filters": {
                        "operator": "and",
                        "conditions": [
                            {"field": "status", "op": "eq", "value": "to_do"}
                        ],
                    },
                },
                "collect": "{{item.name}}",
            },
        )
        output = start_instance(version).node_outputs["each_row"]
        assert output["results"] == ["AC 00", "AC 02", "AC 04"]


@pytest.mark.django_db
class TestPageReadFailure:
    def test_a_failed_page_read_ends_the_loop_instead_of_the_run(self):
        """A permission revoked mid-run makes read_page raise between pages.
        The failure must land on the loop (error entry, loop finishes with the
        items already processed) — not unwind through the already-completed
        body token, where _handle_failure would collect it a second time and
        corrupt the loop state."""
        from unittest import mock

        from automation.workflows import engine
        from automation.workflows.actions import ActionError

        domain = make_domain("Sweep revoked")
        for index in range(4):
            AppliedControl.objects.create(name=f"AC {index:02d}", folder=domain)
        version = paging_flow(
            domain,
            {
                "read": {"model": "applied_control", "order_by": "name", "limit": 2},
                "collect": "{{item.name}}",
            },
        )
        real = engine.read_page
        calls = {"count": 0}

        def revoked_after_first_page(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] > 1:
                raise ActionError("Authorization denied: permission revoked")
            return real(*args, **kwargs)

        with mock.patch.object(engine, "read_page", revoked_after_first_page):
            instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = instance.node_outputs["each_row"]
        assert output["count"] == 2
        assert output["results"] == ["AC 00", "AC 01"]
        assert any("page read failed" in e["message"] for e in output["errors"])
        assert not instance.tokens.filter(status="waiting").exists()


@pytest.mark.django_db
class TestPagingLoopValidation:
    def test_an_invalid_read_is_refused_at_publish(self):
        domain = make_domain("Bad loop read")
        version = paging_flow(domain, {"read": {"model": "not_a_model"}})
        codes = {error["code"] for error in validate_graph(version)}
        assert "action_read_unknown_model" in codes

    def test_a_loop_cannot_do_both(self):
        domain = make_domain("Ambiguous loop")
        version = paging_flow(
            domain,
            {
                "read": {"model": "applied_control"},
                "collection": "{{nodes.something.results}}",
            },
        )
        codes = {error["code"] for error in validate_graph(version)}
        assert "loop_source_ambiguous" in codes

    def test_a_sound_reading_loop_publishes(self):
        domain = make_domain("Good loop read")
        version = paging_flow(
            domain,
            {"read": {"model": "entity", "order_by": "name", "limit": 50}},
        )
        assert validate_graph(version) == []


@pytest.mark.django_db
class TestItemCeiling:
    @override_settings(WORKFLOW_LOOP_MAX_ITEMS=4)
    def test_a_paged_loop_stops_at_the_item_ceiling(self):
        """Pages must not become a way around the item ceiling: a run is
        capped at MAX_STEPS, so an unbounded sweep would fail late rather
        than stop cleanly."""
        domain = make_domain("Sweep item cap")
        for index in range(9):
            AppliedControl.objects.create(name=f"AC {index:02d}", folder=domain)
        version = paging_flow(
            domain,
            {
                "read": {"model": "applied_control", "order_by": "name", "limit": 2},
                "collect": "{{item.name}}",
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = instance.node_outputs["each_row"]
        assert output["count"] == 4
        assert any("stopped after 4 items" in e["message"] for e in output["errors"])
