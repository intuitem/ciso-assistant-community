import uuid

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from iam.models import Folder, User
from pmbok.models import ResponsibilityRole
from workflows.models import Workflow, WorkflowVersion
from workflows.views import WorkflowVersionViewSet, WorkflowViewSet


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="workflow_test_admin@example.com", password="x"
    )


@pytest.fixture
def workflow(db, superuser):
    """A workflow created through the API, which auto-creates draft v1."""
    factory = APIRequestFactory()
    view = WorkflowViewSet.as_view({"post": "create"})
    req = factory.post(
        "/api/workflows/workflows/",
        {"name": "Vendor onboarding", "folder": str(Folder.get_root_folder().id)},
        format="json",
    )
    force_authenticate(req, user=superuser)
    resp = view(req)
    assert resp.status_code == 201, resp.data
    return Workflow.objects.get(id=resp.data["id"])


def _call(action_map, method, url, user, pk=None, data=None):
    factory = APIRequestFactory()
    view = WorkflowVersionViewSet.as_view(action_map)
    req = getattr(factory, method)(url, data, format="json")
    force_authenticate(req, user=user)
    return view(req, pk=pk) if pk else view(req)


def _put_graph(version, payload, user):
    return _call(
        {"put": "graph"},
        "put",
        f"/api/workflows/workflow-versions/{version.id}/graph/",
        user,
        pk=str(version.id),
        data=payload,
    )


def _get_graph(version, user):
    return _call(
        {"get": "graph"},
        "get",
        f"/api/workflows/workflow-versions/{version.id}/graph/",
        user,
        pk=str(version.id),
    )


def _publish(version, user):
    return _call(
        {"post": "publish"},
        "post",
        f"/api/workflows/workflow-versions/{version.id}/publish/",
        user,
        pk=str(version.id),
    )


def _minimal_graph():
    start, task, end = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    return {
        "nodes": [
            {
                "id": start,
                "type": "trigger",
                "trigger_config": {"type": "manual"},
                "position": {"x": 0, "y": 0},
            },
            {
                "id": task,
                "type": "action",
                "label": "Notify",
                "action_config": {"type": "log"},
                "position": {"x": 200, "y": 0},
            },
            {"id": end, "type": "end", "position": {"x": 400, "y": 0}},
        ],
        "edges": [
            {"id": str(uuid.uuid4()), "source": start, "target": task},
            {"id": str(uuid.uuid4()), "source": task, "target": end},
        ],
        "variables": [],
    }


@pytest.mark.django_db
class TestWorkflowCreation:
    def test_create_auto_creates_draft_v1(self, workflow):
        versions = list(workflow.versions.all())
        assert len(versions) == 1
        assert versions[0].version_number == 1
        assert versions[0].status == WorkflowVersion.Status.DRAFT

    def test_version_inherits_workflow_folder(self, workflow):
        assert workflow.versions.first().folder_id == workflow.folder_id


@pytest.mark.django_db
class TestGraphSave:
    def test_roundtrip(self, workflow, superuser):
        version = workflow.draft_version
        resp = _put_graph(version, _minimal_graph(), superuser)
        assert resp.status_code == 200, resp.data
        assert len(resp.data["nodes"]) == 3
        assert len(resp.data["edges"]) == 2

        resp = _get_graph(version, superuser)
        assert resp.status_code == 200
        assert {n["type"] for n in resp.data["nodes"]} == {"trigger", "action", "end"}

    def test_removed_rows_are_deleted(self, workflow, superuser):
        version = workflow.draft_version
        graph = _minimal_graph()
        _put_graph(version, graph, superuser)
        graph["nodes"] = graph["nodes"][:1]
        graph["edges"] = []
        resp = _put_graph(version, graph, superuser)
        assert resp.status_code == 200
        assert version.nodes.count() == 1
        assert version.edges.count() == 0

    def test_variables_and_conditions_roundtrip(self, workflow, superuser):
        version = workflow.draft_version
        graph = _minimal_graph()
        var_id = str(uuid.uuid4())
        graph["variables"] = [{"id": var_id, "key": "decision", "type": "string"}]
        graph["edges"][1]["condition_groups"] = [
            {
                "operator": "and",
                "conditions": [{"variable": var_id, "op": "eq", "value": '"approved"'}],
                "children": [],
            }
        ]
        resp = _put_graph(version, graph, superuser)
        assert resp.status_code == 200, resp.data
        edge = resp.data["edges"][1]
        assert edge["condition_groups"][0]["conditions"][0]["op"] == "eq"

    def test_removing_referenced_variable_fails(self, workflow, superuser):
        version = workflow.draft_version
        graph = _minimal_graph()
        var_id = str(uuid.uuid4())
        graph["variables"] = [{"id": var_id, "key": "decision", "type": "string"}]
        graph["edges"][1]["condition_groups"] = [
            {
                "operator": "and",
                "conditions": [{"variable": var_id, "op": "is_null", "value": ""}],
                "children": [],
            }
        ]
        assert _put_graph(version, graph, superuser).status_code == 200
        # Dropping the variable but keeping the edge that references it must 400:
        # the recreated condition references a variable absent from the payload.
        graph["variables"] = []
        resp = _put_graph(version, graph, superuser)
        assert resp.status_code == 400

    def test_published_version_is_immutable(self, workflow, superuser):
        version = workflow.draft_version
        _put_graph(version, _minimal_graph(), superuser)
        assert _publish(version, superuser).status_code == 200
        resp = _put_graph(version, _minimal_graph(), superuser)
        assert resp.status_code == 400


@pytest.mark.django_db
class TestPublish:
    def test_empty_graph_fails_validation(self, workflow, superuser):
        resp = _publish(workflow.draft_version, superuser)
        assert resp.status_code == 400
        codes = {e["code"] for e in resp.data["errors"]}
        assert "trigger_node_missing" in codes
        assert "end_node_missing" in codes

    def test_unreachable_node_fails_validation(self, workflow, superuser):
        version = workflow.draft_version
        graph = _minimal_graph()
        orphan = str(uuid.uuid4())
        graph["nodes"].append(
            {"id": orphan, "type": "action", "position": {"x": 0, "y": 200}}
        )
        _put_graph(version, graph, superuser)
        resp = _publish(version, superuser)
        assert resp.status_code == 400
        offending = {
            e["node_id"] for e in resp.data["errors"] if e["code"] == "node_unreachable"
        }
        assert orphan in offending

    def test_task_node_without_template_fails_validation(self, workflow, superuser):
        ResponsibilityRole.create_default_roles()
        version = workflow.draft_version
        graph = _minimal_graph()
        graph["nodes"][1]["type"] = "task"
        _put_graph(version, graph, superuser)
        resp = _publish(version, superuser)
        assert resp.status_code == 400
        codes = {e["code"] for e in resp.data["errors"]}
        assert "task_template_missing" in codes

    def test_condition_without_default_branch_fails_validation(
        self, workflow, superuser
    ):
        # A branch node whose every outgoing edge carries a condition can strand
        # a token at runtime; publish must require an "otherwise" branch.
        version = workflow.draft_version
        start, cond, end = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        end2 = str(uuid.uuid4())
        var = str(uuid.uuid4())
        conditioned_edge = str(uuid.uuid4())
        graph = {
            "variables": [{"id": var, "key": "decision", "type": "string"}],
            "nodes": [
                {
                    "id": start,
                    "type": "trigger",
                    "trigger_config": {"type": "manual"},
                    "position": {"x": 0, "y": 0},
                },
                {"id": cond, "type": "condition", "position": {"x": 200, "y": 0}},
                {"id": end, "type": "end", "position": {"x": 400, "y": 0}},
                {"id": end2, "type": "end", "position": {"x": 400, "y": 200}},
            ],
            "edges": [
                {"id": str(uuid.uuid4()), "source": start, "target": cond},
                {
                    "id": conditioned_edge,
                    "source": cond,
                    "target": end,
                    "condition_groups": [
                        {
                            "operator": "and",
                            "conditions": [
                                {"variable": var, "op": "eq", "value": '"yes"'}
                            ],
                        }
                    ],
                },
            ],
        }
        _put_graph(version, graph, superuser)
        resp = _publish(version, superuser)
        assert resp.status_code == 400
        offending = {
            e["node_id"]
            for e in resp.data["errors"]
            if e["code"] == "condition_default_missing"
        }
        assert cond in offending

        # Adding an unconditioned (otherwise) edge makes the node exhaustive.
        graph["edges"].append(
            {"id": str(uuid.uuid4()), "source": cond, "target": end2, "priority": 1}
        )
        _put_graph(version, graph, superuser)
        resp = _publish(version, superuser)
        assert resp.status_code == 200, resp.data

    def test_publish_archives_previous_version(self, workflow, superuser):
        v1 = workflow.draft_version
        _put_graph(v1, _minimal_graph(), superuser)
        assert _publish(v1, superuser).status_code == 200

        resp = _call(
            {"post": "new_draft"},
            "post",
            f"/api/workflows/workflow-versions/{v1.id}/new-draft/",
            superuser,
            pk=str(v1.id),
        )
        assert resp.status_code == 201, resp.data
        v2 = WorkflowVersion.objects.get(id=resp.data["id"])
        assert v2.version_number == 2
        assert _publish(v2, superuser).status_code == 200

        v1.refresh_from_db()
        assert v1.status == WorkflowVersion.Status.ARCHIVED
        assert workflow.published_version == v2


@pytest.mark.django_db
class TestNewDraft:
    def test_clone_copies_graph(self, workflow, superuser):
        v1 = workflow.draft_version
        graph = _minimal_graph()
        var_id = str(uuid.uuid4())
        graph["variables"] = [{"id": var_id, "key": "decision", "type": "string"}]
        graph["edges"][1]["condition_groups"] = [
            {
                "operator": "and",
                "conditions": [{"variable": var_id, "op": "is_null", "value": ""}],
                "children": [],
            }
        ]
        _put_graph(v1, graph, superuser)
        _publish(v1, superuser)

        v2 = v1.clone_as_draft()
        assert v2.status == WorkflowVersion.Status.DRAFT
        assert v2.nodes.count() == v1.nodes.count()
        assert v2.edges.count() == v1.edges.count()
        assert v2.variables.count() == 1
        # Cloned rows are new rows: editing the draft can't touch v1.
        assert not set(v2.nodes.values_list("id", flat=True)) & set(
            v1.nodes.values_list("id", flat=True)
        )
        cloned_condition = (
            v2.edges.filter(condition_groups__isnull=False)
            .first()
            .condition_groups.first()
            .conditions.first()
        )
        assert cloned_condition.variable.version_id == v2.id

    def test_second_draft_is_rejected(self, workflow, superuser):
        v1 = workflow.draft_version
        _put_graph(v1, _minimal_graph(), superuser)
        _publish(v1, superuser)
        resp = _call(
            {"post": "new_draft"},
            "post",
            f"/api/workflows/workflow-versions/{v1.id}/new-draft/",
            superuser,
            pk=str(v1.id),
        )
        assert resp.status_code == 201
        resp = _call(
            {"post": "new_draft"},
            "post",
            f"/api/workflows/workflow-versions/{v1.id}/new-draft/",
            superuser,
            pk=str(v1.id),
        )
        assert resp.status_code == 400
