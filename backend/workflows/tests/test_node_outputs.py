import uuid

import pytest

from iam.models import Folder
from workflows.engine import start_instance
from workflows.graph import GraphValidationError, save_graph
from workflows.models import Workflow, WorkflowInstance, WorkflowVersion
from workflows.tests.helpers import publisher_user


def make_workflow(name="Ref flow"):
    workflow = Workflow.objects.create(name=name, folder=Folder.get_root_folder())
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    return workflow, version


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


@pytest.mark.django_db
class TestNodeRefs:
    def test_refs_auto_generated_from_labels(self):
        _, version = make_workflow()
        start = node("trigger", trigger_config={"type": "manual"})
        fetch = node(
            "action", label="Fetch employee record", action_config={"type": "log"}
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, fetch, end],
                "edges": [edge(start, fetch), edge(fetch, end)],
                "variables": [],
            },
        )
        refs = dict(version.nodes.values_list("label", "ref"))
        assert refs["Fetch employee record"] == "fetch_employee_record"
        assert version.nodes.get(type="trigger").ref == "trigger"

    def test_ref_stable_across_label_rename(self):
        _, version = make_workflow()
        start = node("trigger", trigger_config={"type": "manual"})
        action = node("action", label="Old name", action_config={"type": "log"})
        end = node("end")
        graph = {
            "nodes": [start, action, end],
            "edges": [edge(start, action), edge(action, end)],
            "variables": [],
        }
        document = save_graph(version, graph)
        saved = next(n for n in document["nodes"] if n["id"] == action["id"])
        assert saved["ref"] == "old_name"

        saved["label"] = "New name"
        save_graph(version, document)
        assert version.nodes.get(id=action["id"]).ref == "old_name"

    def test_duplicate_explicit_refs_rejected(self):
        _, version = make_workflow()
        start = node("trigger", trigger_config={"type": "manual"})
        a = node("action", label="A", ref="same", action_config={"type": "log"})
        b = node("action", label="B", ref="same", action_config={"type": "log"})
        end = node("end")
        with pytest.raises(GraphValidationError, match="Duplicate node ref"):
            save_graph(
                version,
                {
                    "nodes": [start, a, b, end],
                    "edges": [edge(start, a), edge(a, b), edge(b, end)],
                    "variables": [],
                },
            )

    def test_invalid_ref_format_rejected(self):
        _, version = make_workflow()
        start = node("trigger", trigger_config={"type": "manual"})
        bad = node("action", ref="Not A Slug!", action_config={"type": "log"})
        end = node("end")
        with pytest.raises(GraphValidationError, match="Invalid node ref"):
            save_graph(
                version,
                {
                    "nodes": [start, bad, end],
                    "edges": [edge(start, bad), edge(bad, end)],
                    "variables": [],
                },
            )


class TestObjectRendering:
    def test_object_references_render_as_json(self):
        from workflows.actions import render

        context = {"nodes": {"fetch": {"body": {"a": 1, "items": [1, 2]}}}}
        rendered = render("payload: {{nodes.fetch.body}}", context)
        assert rendered == 'payload: {"a": 1, "items": [1, 2]}'


@pytest.mark.django_db
class TestNodeOutputReferences:
    def test_chain_via_node_namespace_without_output_mapping(self, monkeypatch):
        from core.models import AppliedControl

        _, version = make_workflow()

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"identity": {"email": "ada@acme.com"}}

        monkeypatch.setattr(
            "requests.request", lambda method, url, **kw: FakeResponse()
        )
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda url, **kw: None
        )

        start = node("trigger", trigger_config={"type": "manual"})
        fetch = node(
            "action",
            label="Fetch",
            action_config={
                "type": "http_request",
                "method": "GET",
                "url": "https://api.example.com/employee",
            },
        )
        create = node(
            "action",
            label="Create",
            action_config={
                "type": "create_object",
                "model": "applied_control",
                # No output_mapping, no declared variables: direct node ref.
                "fields": {"name": "Onboard {{nodes.fetch.body.identity.email}}"},
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, fetch, create, end],
                "edges": [edge(start, fetch), edge(fetch, create), edge(create, end)],
                "variables": [],
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, list(
            instance.logs.values_list("message", flat=True)
        )
        assert AppliedControl.objects.filter(name="Onboard ada@acme.com").exists()
        assert instance.node_outputs["fetch"]["body"]["identity"]["email"] == (
            "ada@acme.com"
        )

    def test_large_outputs_are_capped_but_stay_navigable(self, monkeypatch):
        _, version = make_workflow()

        class FakeResponse:
            status_code = 200

            def json(self):
                return {
                    "blob": "x" * 50000,
                    "nested": {"deep": {"email": "ada@acme.com"}},
                    "items": list(range(500)),
                }

        monkeypatch.setattr(
            "requests.request", lambda method, url, **kw: FakeResponse()
        )
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda url, **kw: None
        )

        start = node("trigger", trigger_config={"type": "manual"})
        fetch = node(
            "action",
            label="Big fetch",
            action_config={
                "type": "http_request",
                "method": "GET",
                "url": "https://api.example.com/big",
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, fetch, end],
                "edges": [edge(start, fetch), edge(fetch, end)],
                "variables": [],
            },
        )
        instance = start_instance(version)
        stored = instance.node_outputs["big_fetch"]["body"]
        # Structure survives: nested paths remain referenceable.
        assert isinstance(stored, dict)
        assert stored["nested"]["deep"]["email"] == "ada@acme.com"
        # Oversized leaves truncate, huge lists tail-omit.
        assert "truncated" in stored["blob"]
        assert len(stored["blob"]) < 1200
        assert "more items" in stored["items"][-1]
        assert len(stored["items"]) <= 101
