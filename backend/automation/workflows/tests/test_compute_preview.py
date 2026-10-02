"""The editor's compute-row preview: the engine's evaluator, answered live."""

import uuid

import pytest
from django.contrib.auth.models import Permission
from rest_framework.test import APIRequestFactory, force_authenticate

from iam.models import Folder, Role, RoleAssignment, User
from automation.workflows.engine import start_instance, trigger_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import Workflow, WorkflowVersion
from automation.workflows.preview import preview_compute_rows, type_name
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


def row(key, expression):
    return {"key": key, "expression": expression}


def make_domain(name):
    return Folder.objects.create(
        name=name,
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def build(name="Preview", variables=None, steps=None, folder=None):
    """Manual trigger -> the given action nodes -> end, as a draft version."""
    workflow = Workflow.objects.create(
        name=name, folder=folder or Folder.get_root_folder()
    )
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


def grant(user, folder, *codenames):
    """A bespoke role holding `codenames` (plus view_folder, which every real
    role has and the kernel's scoping relies on) on `folder`."""
    role = Role.objects.create(name=f"role-{uuid.uuid4()}")
    role.permissions.set(
        Permission.objects.filter(codename__in=[*codenames, "view_folder"])
    )
    assignment = RoleAssignment.objects.create(
        user=user, role=role, folder=folder, is_recursive=True
    )
    assignment.perimeter_folders.add(folder)
    return assignment


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
class TestPreviewComputeRows:
    def test_draft_defaults_answer_without_a_run(self):
        version = build(
            variables=[var("likelihood", default=4), var("impact", default=4)]
        )
        assert preview_compute_rows(version, [row("score", "likelihood * impact")]) == [
            {"ok": True, "value": 16, "type": "int"}
        ]
        # The engine seeds are there too, and there are no node outputs yet.
        results = preview_compute_rows(
            version, [row("a", "size(today)"), row("b", "has(nodes.fetch)")]
        )
        assert [r["value"] for r in results] == [10, False]

    def test_rows_run_in_order_and_see_the_ones_above(self):
        version = build(variables=[var("done", default=1), var("total", default=4)])
        results = preview_compute_rows(
            version,
            [
                row("ratio", "double(done) / double(total)"),
                row("percent", "round(ratio * 100.0, 1)"),
            ],
        )
        assert results == [
            {"ok": True, "value": 0.25, "type": "double"},
            {"ok": True, "value": 25.0, "type": "double"},
        ]

    def test_a_failing_row_is_named_by_the_rows_that_read_it(self):
        version = build(variables=[var("n", default=1)])
        results = preview_compute_rows(
            version,
            [
                row("x", "n / 0"),
                row("y", "x + 1"),
                row("z", "n + 1"),
                row("w", "y * 2"),
            ],
        )
        assert results[0] == {"ok": False, "error": "division by zero"}
        assert results[1] == {"ok": False, "error": "'x' (a row above) failed"}
        assert results[2] == {"ok": True, "value": 2, "type": "int"}
        # Transitive: w reads y, which failed because x did.
        assert results[3] == {"ok": False, "error": "'y' (a row above) failed"}

    def test_blank_rows_answer_none(self):
        version = build(variables=[var("n", default=2)])
        assert preview_compute_rows(version, [row("later", ""), row("d", "n * 2")]) == [
            None,
            {"ok": True, "value": 4, "type": "int"},
        ]

    def test_evaluation_errors_are_answers(self):
        version = build(variables=[var("n", default=2), var("s", "string", "x")])
        results = preview_compute_rows(version, [row("a", "n * s"), row("b", "n +")])
        assert results[0] == {"ok": False, "error": "'*' cannot combine int and string"}
        assert results[1]["ok"] is False
        assert results[1]["error"].startswith("syntax error")

    def test_a_reference_run_supplies_variables_and_node_outputs(self):
        version = build(
            variables=[var("n", default=3)],
            steps=[("Note", "note", {"type": "log", "message": "hello"})],
        )
        instance = trigger_instance(version, initial_variables={"n": 5})
        results = preview_compute_rows(
            version, [row("p", "n * size(nodes.note.message)")], instance=instance
        )
        assert results == [{"ok": True, "value": 25, "type": "int"}]


@pytest.mark.django_db
class TestPreviewEndpoint:
    @pytest.fixture
    def admin(self):
        return User.objects.create_superuser(
            email="preview_admin@tests.local", password="x"
        )

    def test_answers_one_result_per_row(self, admin):
        version = build(variables=[var("a", default=3), var("b", default=2.5)])
        resp = post_preview(version, admin, {"rows": [row("p", "a * b"), row("q", "")]})
        assert resp.status_code == 200
        assert resp.data == {
            "results": [{"ok": True, "value": 7.5, "type": "double"}, None]
        }

    def test_evaluation_failure_is_200_not_ok(self, admin):
        version = build()
        resp = post_preview(version, admin, {"rows": [row("p", "missing + 1")]})
        assert resp.status_code == 200
        assert resp.data["results"][0]["ok"] is False
        assert "not a variable" in resp.data["results"][0]["error"]

    def test_reference_run_of_this_workflow(self, admin):
        version = build(variables=[var("n", default=1)])
        instance = trigger_instance(version, initial_variables={"n": 7})
        resp = post_preview(
            version,
            admin,
            {"rows": [row("p", "n + 1")], "reference_run": str(instance.id)},
        )
        assert resp.data == {"results": [{"ok": True, "value": 8, "type": "int"}]}

    def test_another_workflows_run_is_refused(self, admin):
        version = build(variables=[var("n", default=1)])
        other = build(name="Other", variables=[var("n", default=99)])
        stranger = start_instance(other)
        resp = post_preview(
            version, admin, {"rows": [row("p", "n")], "reference_run": str(stranger.id)}
        )
        assert resp.status_code == 400
        assert resp.data == {"error": "referenceRunNotFound"}

    def test_a_non_uuid_run_id_is_refused_not_a_500(self, admin):
        version = build()
        resp = post_preview(
            version, admin, {"rows": [row("p", "1")], "reference_run": "abc"}
        )
        assert resp.status_code == 400
        assert resp.data == {"error": "referenceRunNotFound"}

    def test_a_run_the_user_cannot_view_is_refused(self):
        """Seeing the version is not seeing every run: instances keep their
        folder when a workflow moves. A reader of the workflow's domain must
        not read a run that sits in another domain through `nodes`."""
        home, elsewhere = make_domain("Home"), make_domain("Elsewhere")
        version = build(
            variables=[var("n", default=1)],
            steps=[("Note", "note", {"type": "log", "message": "secret"})],
            folder=home,
        )
        instance = start_instance(version)
        instance.folder = elsewhere
        instance.save(update_fields=["folder"])
        reader = User.objects.create_user(email="reader@tests.local", password="x")
        grant(
            reader,
            home,
            "view_workflow",
            "view_workflowversion",
            "view_workflowinstance",
        )
        refused = post_preview(
            version,
            reader,
            {"rows": [row("p", "nodes")], "reference_run": str(instance.id)},
        )
        assert refused.status_code == 400
        assert refused.data == {"error": "referenceRunNotFound"}
        # The same reader may use a run they can see.
        instance.folder = home
        instance.save(update_fields=["folder"])
        allowed = post_preview(
            version,
            reader,
            {
                "rows": [row("p", "nodes.note.message")],
                "reference_run": str(instance.id),
            },
        )
        assert allowed.status_code == 200
        assert allowed.data["results"][0]["value"] == "secret"

    def test_oversized_requests_are_refused_with_a_code_only(self, admin):
        version = build()
        resp = post_preview(version, admin, {"rows": [row("p", "1 + " * 1000)]})
        assert resp.status_code == 400
        # A stable code, never exception text: nothing about the server leaks.
        assert resp.data == {"error": "previewExpressionTooLong"}
        assert post_preview(version, admin, {"rows": [row("k", "1")] * 51}).data == {
            "error": "previewRowsInvalid"
        }
        assert post_preview(version, admin, {"rows": "nope"}).data == {
            "error": "previewRowsInvalid"
        }
        assert post_preview(version, admin, {}).data == {"error": "previewRowsInvalid"}
