import uuid

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from iam.models import Folder, User
from pmbok.models import ResponsibilityRole
from automation.workflows.models import Workflow, WorkflowVersion
from automation.workflows.views import WorkflowVersionViewSet, WorkflowViewSet


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


def _condition_graph(op="eq", value='"approved"', with_default=True, wire_default=True):
    """trigger -> condition -> {matching branch -> end, default branch -> end2}.

    Conditions live on the condition node's branches; edges only
    reference a branch via ``source_branch``. Returns (graph, ids) so callers
    can assert on / tweak specific rows.
    """
    ids = {
        k: str(uuid.uuid4())
        for k in [
            "start",
            "cond",
            "end",
            "end2",
            "var",
            "match_branch",
            "default_branch",
        ]
    }
    branches = [
        {
            "id": ids["match_branch"],
            "name": "approved",
            "order": 0,
            "is_default": False,
            "condition_groups": [
                {
                    "operator": "and",
                    "conditions": [{"variable": ids["var"], "op": op, "value": value}],
                    "children": [],
                }
            ],
        }
    ]
    if with_default:
        branches.append(
            {
                "id": ids["default_branch"],
                "name": "otherwise",
                "order": 1,
                "is_default": True,
                "condition_groups": [],
            }
        )
    edges = [
        {"id": str(uuid.uuid4()), "source": ids["start"], "target": ids["cond"]},
        {
            "id": str(uuid.uuid4()),
            "source": ids["cond"],
            "target": ids["end"],
            "source_branch": ids["match_branch"],
        },
    ]
    if with_default and wire_default:
        edges.append(
            {
                "id": str(uuid.uuid4()),
                "source": ids["cond"],
                "target": ids["end2"],
                "source_branch": ids["default_branch"],
            }
        )
    graph = {
        "variables": [{"id": ids["var"], "key": "decision", "type": "string"}],
        "nodes": [
            {
                "id": ids["start"],
                "type": "trigger",
                "trigger_config": {"type": "manual"},
                "position": {"x": 0, "y": 0},
            },
            {
                "id": ids["cond"],
                "type": "condition",
                "branches": branches,
                "position": {"x": 200, "y": 0},
            },
            {"id": ids["end"], "type": "end", "position": {"x": 400, "y": 0}},
            {"id": ids["end2"], "type": "end", "position": {"x": 400, "y": 200}},
        ],
        "edges": edges,
    }
    return graph, ids


@pytest.mark.django_db
class TestWorkflowCreation:
    def test_create_auto_creates_draft_v1(self, workflow):
        versions = list(workflow.versions.all())
        assert len(versions) == 1
        assert versions[0].version_number == 1
        assert versions[0].status == WorkflowVersion.Status.DRAFT

    def test_version_inherits_workflow_folder(self, workflow):
        assert workflow.versions.first().folder_id == workflow.folder_id

    def test_list_filters_by_is_active(self, superuser):
        root = Folder.get_root_folder()
        Workflow.objects.create(name="Live", folder=root, is_active=True)
        Workflow.objects.create(name="Paused", folder=root, is_active=False)
        factory = APIRequestFactory()
        view = WorkflowViewSet.as_view({"get": "list"})

        req = factory.get("/api/workflows/workflows/?is_active=false")
        force_authenticate(req, user=superuser)
        names = {row["name"] for row in view(req).data["results"]}
        assert names == {"Paused"}

        req = factory.get("/api/workflows/workflows/?is_active=true")
        force_authenticate(req, user=superuser)
        names = {row["name"] for row in view(req).data["results"]}
        assert names == {"Live"}

    def test_list_shows_and_filters_trigger_types(self, superuser):
        root = Folder.get_root_folder()
        manual_wf = Workflow.objects.create(name="Manual only", folder=root)
        _put_graph(
            WorkflowVersion.objects.create(workflow=manual_wf),
            _minimal_graph(),
            superuser,
        )
        sched_wf = Workflow.objects.create(name="Nightly", folder=root)
        graph = _minimal_graph()
        graph["nodes"][0]["trigger_config"] = {
            "type": "schedule",
            "cron_expression": "0 9 * * 1",
        }
        _put_graph(WorkflowVersion.objects.create(workflow=sched_wf), graph, superuser)

        factory = APIRequestFactory()
        view = WorkflowViewSet.as_view({"get": "list"})
        req = factory.get("/api/workflows/workflows/")
        force_authenticate(req, user=superuser)
        rows = {row["name"]: row["trigger_types"] for row in view(req).data["results"]}
        assert rows["Manual only"] == ["manual"]
        assert rows["Nightly"] == ["schedule"]

        req = factory.get("/api/workflows/workflows/?trigger_type=schedule")
        force_authenticate(req, user=superuser)
        names = {row["name"] for row in view(req).data["results"]}
        assert names == {"Nightly"}


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
        graph, ids = _condition_graph(op="eq", value='"approved"')
        resp = _put_graph(version, graph, superuser)
        assert resp.status_code == 200, resp.data

        # The condition lives on the matching branch of the condition node...
        cond = next(n for n in resp.data["nodes"] if n["id"] == ids["cond"])
        branch = next(b for b in cond["branches"] if b["id"] == ids["match_branch"])
        assert branch["is_default"] is False
        assert branch["condition_groups"][0]["conditions"][0]["op"] == "eq"
        assert branch["condition_groups"][0]["conditions"][0]["value"] == '"approved"'
        default = next(b for b in cond["branches"] if b["id"] == ids["default_branch"])
        assert default["is_default"] is True
        assert default["condition_groups"] == []

        # ...and the edge only references the branch — no conditions on edges.
        wired = next(
            e for e in resp.data["edges"] if e["source_branch"] == ids["match_branch"]
        )
        assert wired["target"] == ids["end"]
        assert "condition_groups" not in wired

    def test_removing_referenced_variable_fails(self, workflow, superuser):
        version = workflow.draft_version
        graph, _ = _condition_graph(op="is_null", value="")
        assert _put_graph(version, graph, superuser).status_code == 200
        # Dropping the variable but keeping the branch that references it must
        # 400: the recreated condition references a variable absent from the
        # payload.
        graph["variables"] = []
        resp = _put_graph(version, graph, superuser)
        assert resp.status_code == 400

    def test_published_version_is_immutable(self, workflow, superuser):
        version = workflow.draft_version
        _put_graph(version, _minimal_graph(), superuser)
        assert _publish(version, superuser).status_code == 200
        resp = _put_graph(version, _minimal_graph(), superuser)
        assert resp.status_code == 400

    def test_subprocess_nodes_are_rejected(self, workflow, superuser):
        # Subprocess authoring is disabled for v1: the graph endpoint refuses a
        # payload that carries a subprocess node, even for a superuser.
        version = workflow.draft_version
        graph = _minimal_graph()
        graph["nodes"].append(
            {
                "id": str(uuid.uuid4()),
                "type": "subprocess",
                "position": {"x": 600, "y": 0},
            }
        )
        resp = _put_graph(version, graph, superuser)
        assert resp.status_code == 400
        assert resp.data["error"] == "subprocessNodesUnavailable"
        # Nothing was persisted: the draft has no subprocess node.
        assert not version.nodes.filter(type="subprocess").exists()


@pytest.mark.django_db
class TestPublish:
    def test_empty_graph_fails_validation(self, workflow, superuser):
        resp = _publish(workflow.draft_version, superuser)
        assert resp.status_code == 400
        codes = {e["code"] for e in resp.data["errors"]}
        assert "trigger_node_missing" in codes

    def test_dangling_step_is_a_valid_terminal(self, workflow, superuser):
        """An unwired last step just ends that branch: no end node
        required, and no nag about the missing edge."""
        version = workflow.draft_version
        trigger, action = str(uuid.uuid4()), str(uuid.uuid4())
        graph = {
            "nodes": [
                {
                    "id": trigger,
                    "type": "trigger",
                    "trigger_config": {"type": "manual"},
                    "position": {"x": 0, "y": 0},
                },
                {
                    "id": action,
                    "type": "action",
                    "action_config": {"type": "log", "message": "done"},
                    "position": {"x": 200, "y": 0},
                },
            ],
            "edges": [{"id": str(uuid.uuid4()), "source": trigger, "target": action}],
            "variables": [],
        }
        assert _put_graph(version, graph, superuser).status_code == 200
        assert _publish(version, superuser).status_code == 200

    def test_cycle_with_no_exit_fails_validation(self, workflow, superuser):
        """The one structural check left: a loop of steps that can reach no
        terminal could never finish."""
        version = workflow.draft_version
        trigger, a, b = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        graph = {
            "nodes": [
                {
                    "id": trigger,
                    "type": "trigger",
                    "trigger_config": {"type": "manual"},
                    "position": {"x": 0, "y": 0},
                },
                {
                    "id": a,
                    "type": "action",
                    "action_config": {"type": "log"},
                    "position": {"x": 200, "y": 0},
                },
                {
                    "id": b,
                    "type": "action",
                    "action_config": {"type": "log"},
                    "position": {"x": 400, "y": 0},
                },
            ],
            "edges": [
                {"id": str(uuid.uuid4()), "source": trigger, "target": a},
                {"id": str(uuid.uuid4()), "source": a, "target": b},
                {"id": str(uuid.uuid4()), "source": b, "target": a},
            ],
            "variables": [],
        }
        assert _put_graph(version, graph, superuser).status_code == 200
        resp = _publish(version, superuser)
        assert resp.status_code == 400
        codes = {e["code"] for e in resp.data["errors"]}
        assert "dead_end" in codes

    def test_stop_node_cannot_be_followed(self, workflow, superuser):
        """end_has_outgoing is load-bearing now: it is what guarantees stop
        nodes are leaves, which the dead_end rule relies on."""
        from automation.workflows.models import WorkflowEdge, WorkflowNode
        from automation.workflows.validation import validate_graph

        version = workflow.draft_version
        _put_graph(version, _minimal_graph(), superuser)
        stop = version.nodes.get(type=WorkflowNode.Type.END)
        trailing = WorkflowNode.objects.create(
            version=version, type=WorkflowNode.Type.ACTION, label="After the stop"
        )
        WorkflowEdge.objects.create(
            version=version, source_node=stop, target_node=trailing
        )
        codes = {e["code"] for e in validate_graph(version)}
        assert "end_has_outgoing" in codes

    def test_all_condition_branches_may_be_leaves(self, workflow, superuser):
        """Every branch of a decision can simply stop, with no stop node."""
        version = workflow.draft_version
        trigger, gate, yes, no = (str(uuid.uuid4()) for _ in range(4))
        var, match_branch, default_branch = (str(uuid.uuid4()) for _ in range(3))
        graph = {
            "nodes": [
                {
                    "id": trigger,
                    "type": "trigger",
                    "trigger_config": {"type": "manual"},
                    "input_mapping": {"decision": "decision"},
                    "position": {"x": 0, "y": 0},
                },
                {
                    "id": gate,
                    "type": "condition",
                    "label": "Gate",
                    "position": {"x": 200, "y": 0},
                    "branches": [
                        {
                            "id": match_branch,
                            "name": "yes",
                            "order": 0,
                            "is_default": False,
                            "condition_groups": [
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {"variable": var, "op": "eq", "value": "go"}
                                    ],
                                    "children": [],
                                }
                            ],
                        },
                        {
                            "id": default_branch,
                            "name": "otherwise",
                            "order": 1,
                            "is_default": True,
                            "condition_groups": [],
                        },
                    ],
                },
                {
                    "id": yes,
                    "type": "action",
                    "action_config": {"type": "log"},
                    "position": {"x": 400, "y": -60},
                },
                {
                    "id": no,
                    "type": "action",
                    "action_config": {"type": "log"},
                    "position": {"x": 400, "y": 60},
                },
            ],
            "edges": [
                {"id": str(uuid.uuid4()), "source": trigger, "target": gate},
                {
                    "id": str(uuid.uuid4()),
                    "source": gate,
                    "target": yes,
                    "source_branch": match_branch,
                },
                {
                    "id": str(uuid.uuid4()),
                    "source": gate,
                    "target": no,
                    "source_branch": default_branch,
                },
            ],
            "variables": [{"id": var, "key": "decision", "type": "string"}],
        }
        assert _put_graph(version, graph, superuser).status_code == 200
        assert _publish(version, superuser).status_code == 200

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
        # A branch node whose every branch carries a condition can strand a
        # token at runtime; publish must require a default ("otherwise") branch.
        version = workflow.draft_version
        graph, ids = _condition_graph(op="eq", value='"yes"', with_default=False)
        _put_graph(version, graph, superuser)
        resp = _publish(version, superuser)
        assert resp.status_code == 400
        offending = {
            e["node_id"]
            for e in resp.data["errors"]
            if e["code"] == "condition_default_missing"
        }
        assert ids["cond"] in offending

        # Adding a wired default branch makes the node exhaustive.
        graph, ids = _condition_graph(op="eq", value='"yes"', with_default=True)
        _put_graph(version, graph, superuser)
        resp = _publish(version, superuser)
        assert resp.status_code == 200, resp.data

    def test_unwired_branch_fails_validation(self, workflow, superuser):
        # A defined branch with no outgoing edge routes nowhere; publish must
        # reject it even when a default branch is present.
        version = workflow.draft_version
        graph, ids = _condition_graph(op="eq", value='"yes"', with_default=True)
        cond = next(n for n in graph["nodes"] if n["id"] == ids["cond"])
        stray_branch = str(uuid.uuid4())
        cond["branches"].append(
            {
                "id": stray_branch,
                "name": "stray",
                "order": 2,
                "is_default": False,
                "condition_groups": [
                    {
                        "operator": "and",
                        "conditions": [
                            {"variable": ids["var"], "op": "eq", "value": '"no"'}
                        ],
                        "children": [],
                    }
                ],
            }
        )
        _put_graph(version, graph, superuser)
        resp = _publish(version, superuser)
        assert resp.status_code == 400
        offending = {
            e["node_id"] for e in resp.data["errors"] if e["code"] == "branch_unwired"
        }
        assert ids["cond"] in offending

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
        graph, ids = _condition_graph(op="is_null", value="")
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
        # The clone preserves the condition node's branches (with their
        # condition trees) and the wiring that references them. ConditionGroup
        # now hangs off the branch/node, not the edge.
        cond = v2.nodes.get(type="condition")
        branches = list(cond.branches.all())
        assert len(branches) == 2
        assert any(b.is_default for b in branches)
        matching = next(b for b in branches if not b.is_default)
        cloned_condition = matching.condition_groups.first().conditions.first()
        assert cloned_condition.variable.version_id == v2.id
        # Every branch is wired by a cloned edge that carries its source_branch.
        wired_branch_ids = {
            e.source_branch_id for e in v2.edges.all() if e.source_branch_id is not None
        }
        assert wired_branch_ids == {b.id for b in branches}

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


@pytest.mark.django_db
class TestDiscardDraft:
    def _discard(self, version, user):
        return _call(
            {"post": "discard"},
            "post",
            f"/api/workflows/workflow-versions/{version.id}/discard/",
            user,
            pk=str(version.id),
        )

    def test_discard_falls_back_to_published(self, workflow, superuser):
        v1 = workflow.draft_version
        _put_graph(v1, _minimal_graph(), superuser)
        _publish(v1, superuser)
        _call(
            {"post": "new_draft"},
            "post",
            f"/api/workflows/workflow-versions/{v1.id}/new-draft/",
            superuser,
            pk=str(v1.id),
        )
        draft = workflow.draft_version
        # Give the draft a condition node with branches: discarding must clear
        # the PROTECTed condition tree before the cascade.
        graph, _ = _condition_graph()
        _put_graph(draft, graph, superuser)

        resp = self._discard(draft, superuser)
        assert resp.status_code == 200, resp.data
        assert resp.data["published_id"] == str(v1.id)
        workflow.refresh_from_db()
        assert workflow.draft_version is None
        assert workflow.published_version.id == v1.id

    def test_discard_refused_without_published_fallback(self, workflow, superuser):
        draft = workflow.draft_version
        _put_graph(draft, _minimal_graph(), superuser)
        resp = self._discard(draft, superuser)
        assert resp.status_code == 400
        assert resp.data["error"] == "noPublishedVersionToFallBackTo"

    def test_discard_refused_on_published_version(self, workflow, superuser):
        v1 = workflow.draft_version
        _put_graph(v1, _minimal_graph(), superuser)
        _publish(v1, superuser)
        resp = self._discard(v1, superuser)
        assert resp.status_code == 400
        assert resp.data["error"] == "onlyDraftVersionsCanBeDiscarded"
