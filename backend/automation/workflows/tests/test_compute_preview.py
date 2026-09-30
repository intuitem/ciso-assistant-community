"""The editor's compute-row preview: the engine's evaluator, answered live."""

import uuid

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from iam.models import Folder, User
from automation.workflows.engine import start_instance, trigger_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import Workflow, WorkflowVersion
from automation.workflows.preview import preview_compute_row, type_name
from automation.workflows.tests.helpers import publisher_user
from automation.workflows.views import WorkflowVersionViewSet


def node(type_, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(source, target):
    return {"id": str(uuid.uuid4()), "source": source["id"], "target": target["id"]}


def var(key, type_="number", default=None):
    return {
        "id": str(uuid.uuid4()),
        "key": key,
        "type": type_,
        "default_value": default,
    }


def build(name="Preview", variables=None, steps=None):
    """Manual trigger -> the given action nodes -> end, as a draft version."""
    workflow = Workflow.objects.create(name=name, folder=Folder.get_root_folder())
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", trigger_config={"type": "manual"})
    middle = [
        node("action", label=label, ref=ref, action_config=config)
        for label, ref, config in (steps or [])
    ]
    end = node("end")
    chain = [start, *middle, end]
    save_graph(
        version,
        {
            "nodes": chain,
            "edges": [edge(a, b) for a, b in zip(chain, chain[1:])],
            "variables": variables or [],
        },
    )
    return version


def post_preview(version, user, body):
    factory = APIRequestFactory()
    view = WorkflowVersionViewSet.as_view({"post": "preview_expression"})
    req = factory.post(
        f"/api/workflows/workflow-versions/{version.id}/preview-expression/",
        body,
        format="json",
    )
    force_authenticate(req, user=user)
    return view(req, pk=str(version.id))


class TestTypeName:
    def test_names_the_types_an_author_cares_about(self):
        assert type_name(16) == "int"
        assert type_name(7.5) == "double"
        assert type_name(True) == "bool"
        assert type_name("high") == "string"
        assert type_name([1]) == "list"
        assert type_name({"a": 1}) == "map"
        assert type_name(None) == "null"


@pytest.mark.django_db
class TestPreviewComputeRow:
    def test_draft_defaults_answer_without_a_run(self):
        version = build(
            variables=[var("likelihood", default=4), var("impact", default=4)]
        )
        assert preview_compute_row(version, "likelihood * impact") == {
            "ok": True,
            "value": 16,
            "type": "int",
        }
        # The engine seeds are there too, and there are no node outputs yet.
        assert preview_compute_row(version, "size(today)")["value"] == 10
        assert preview_compute_row(version, "has(nodes.fetch)")["value"] is False

    def test_rows_above_run_first_in_order(self):
        version = build(variables=[var("done", default=1), var("total", default=4)])
        result = preview_compute_row(
            version,
            "round(ratio * 100.0, 1)",
            rows_above=[{"key": "ratio", "expression": "double(done) / double(total)"}],
        )
        assert result == {"ok": True, "value": 25.0, "type": "double"}

    def test_a_failing_row_above_is_named(self):
        version = build(variables=[var("n", default=1)])
        result = preview_compute_row(
            version, "x + 1", rows_above=[{"key": "x", "expression": "n / 0"}]
        )
        assert result["ok"] is False
        assert "'x' (a row above) failed: division by zero" == result["error"]

    def test_blank_rows_above_are_skipped(self):
        version = build(variables=[var("n", default=2)])
        result = preview_compute_row(
            version, "n * 2", rows_above=[{"key": "later", "expression": ""}]
        )
        assert result == {"ok": True, "value": 4, "type": "int"}

    def test_evaluation_errors_are_answers(self):
        version = build(variables=[var("n", default=2), var("s", "string", "x")])
        assert preview_compute_row(version, "n * s") == {
            "ok": False,
            "error": "'*' cannot combine int and string",
        }
        assert preview_compute_row(version, "n +")["ok"] is False

    def test_a_reference_run_supplies_variables_and_node_outputs(self):
        version = build(
            variables=[var("n", default=3)],
            steps=[("Note", "note", {"type": "log", "message": "hello"})],
        )
        instance = trigger_instance(version, initial_variables={"n": 5})
        result = preview_compute_row(
            version, "n * size(nodes.note.message)", instance=instance
        )
        assert result == {"ok": True, "value": 25, "type": "int"}


@pytest.mark.django_db
class TestPreviewEndpoint:
    @pytest.fixture
    def admin(self):
        return User.objects.create_superuser(
            email="preview_admin@tests.local", password="x"
        )

    def test_answers_with_value_and_type(self, admin):
        version = build(variables=[var("a", default=3), var("b", default=2.5)])
        resp = post_preview(version, admin, {"expression": "a * b"})
        assert resp.status_code == 200
        assert resp.data == {"ok": True, "value": 7.5, "type": "double"}

    def test_evaluation_failure_is_200_not_ok(self, admin):
        version = build()
        resp = post_preview(version, admin, {"expression": "missing + 1"})
        assert resp.status_code == 200
        assert resp.data["ok"] is False
        assert "not a variable" in resp.data["error"]

    def test_reference_run_of_this_workflow(self, admin):
        version = build(variables=[var("n", default=1)])
        instance = trigger_instance(version, initial_variables={"n": 7})
        resp = post_preview(
            version, admin, {"expression": "n + 1", "reference_run": str(instance.id)}
        )
        assert resp.data == {"ok": True, "value": 8, "type": "int"}

    def test_another_workflows_run_is_refused(self, admin):
        version = build(variables=[var("n", default=1)])
        other = build(name="Other", variables=[var("n", default=99)])
        stranger = start_instance(other)
        resp = post_preview(
            version, admin, {"expression": "n", "reference_run": str(stranger.id)}
        )
        assert resp.status_code == 400
        assert resp.data == {"error": "referenceRunNotFound"}

    def test_oversized_requests_are_refused(self, admin):
        version = build()
        assert (
            post_preview(version, admin, {"expression": "1 + " * 1000}).status_code
            == 400
        )
        assert (
            post_preview(
                version,
                admin,
                {
                    "expression": "1",
                    "rows_above": [{"key": "k", "expression": "1"}] * 51,
                },
            ).status_code
            == 400
        )
        assert (
            post_preview(
                version, admin, {"expression": "1", "rows_above": "nope"}
            ).status_code
            == 400
        )
