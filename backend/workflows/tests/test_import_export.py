import uuid

import pytest
import yaml
from rest_framework.test import APIRequestFactory, force_authenticate

from core.models import TaskTemplate
from iam.models import Folder, User
from workflows.graph import save_graph
from workflows.import_export import (
    WorkflowImportError,
    export_workflow,
    import_workflow,
)
from workflows.models import Workflow, WorkflowVersion
from workflows.views import WorkflowViewSet
from workflows.tests.helpers import publisher_user


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="workflow_ie_admin@example.com", password="x"
    )


@pytest.fixture
def root(db):
    return Folder.get_root_folder()


def _rich_graph():
    n = {
        k: str(uuid.uuid4())
        for k in [
            "hook",
            "nightly",
            "incident",
            "fetch",
            "gate",
            "end",
            "e1",
            "e2",
            "e3",
            "e4",
            "e5",
            "e6",
            "bapp",
            "bdef",
            "v1",
            "v2",
        ]
    }
    return n, {
        "variables": [
            {"id": n["v1"], "key": "employee_id", "type": "string"},
            {
                "id": n["v2"],
                "key": "approved",
                "type": "boolean",
                "default_value": False,
            },
        ],
        "nodes": [
            {
                "id": n["hook"],
                "type": "trigger",
                "ref": "hook",
                "trigger_config": {"type": "webhook"},
                "input_mapping": {"employee_id": "data.id"},
                "position": {"x": 0, "y": 0},
            },
            {
                "id": n["nightly"],
                "type": "trigger",
                "ref": "nightly",
                "trigger_config": {
                    "type": "schedule",
                    "cron_expression": "0 2 * * *",
                    "timezone": "UTC",
                },
                "position": {"x": 0, "y": 120},
            },
            {
                "id": n["incident"],
                "type": "trigger",
                "ref": "on_incident",
                "trigger_config": {
                    "type": "internal_event",
                    "event_key": "incident.created",
                    "filters": {
                        "operator": "and",
                        "conditions": [
                            {"field": "severity", "op": "lte", "value": "2"}
                        ],
                    },
                },
                "position": {"x": 0, "y": 240},
            },
            {
                "id": n["fetch"],
                "type": "action",
                "label": "Fetch employee",
                "action_config": {
                    "type": "http_request",
                    "url": "https://hris.example.com/{{employee_id}}",
                    "headers": {"Authorization": "Bearer {{secrets.hris_token}}"},
                },
                "retry_max_attempts": 3,
                "retry_delay_seconds": 30,
                "retry_backoff": "exponential",
                "position": {"x": 200, "y": 120},
            },
            {
                "id": n["gate"],
                "type": "condition",
                "label": "Gate",
                "position": {"x": 400, "y": 120},
                # Conditions live on the condition node's branches (spec D25);
                # edges only reference a branch via source_branch.
                "branches": [
                    {
                        "id": n["bapp"],
                        "name": "approved",
                        "order": 0,
                        "is_default": False,
                        "condition_groups": [
                            {
                                "operator": "and",
                                "conditions": [
                                    {"variable": n["v2"], "op": "eq", "value": "true"}
                                ],
                                "children": [],
                            }
                        ],
                    },
                    {
                        "id": n["bdef"],
                        "name": "otherwise",
                        "order": 1,
                        "is_default": True,
                        "condition_groups": [],
                    },
                ],
            },
            {"id": n["end"], "type": "end", "position": {"x": 600, "y": 120}},
        ],
        "edges": [
            {"id": n["e1"], "source": n["hook"], "target": n["fetch"]},
            {"id": n["e2"], "source": n["nightly"], "target": n["fetch"]},
            {"id": n["e3"], "source": n["incident"], "target": n["fetch"]},
            {"id": n["e4"], "source": n["fetch"], "target": n["gate"]},
            {
                "id": n["e5"],
                "source": n["gate"],
                "target": n["end"],
                "label": "approved",
                "source_branch": n["bapp"],
            },
            {
                "id": n["e6"],
                "source": n["gate"],
                "target": n["end"],
                "source_branch": n["bdef"],
            },
        ],
    }


@pytest.fixture
def rich_workflow(db, root):
    workflow = Workflow.objects.create(
        name="HRIS sync", description="Sync HRIS", folder=root
    )
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    _, payload = _rich_graph()
    save_graph(version, payload)
    version.publish(publisher_user())
    hook = workflow.triggers.get(node_ref="hook")
    hook.hmac_secret = "hmac-secret-value"
    hook.save(update_fields=["hmac_secret"])
    return workflow


@pytest.mark.django_db
class TestExport:
    def test_portable_shape(self, rich_workflow):
        data = export_workflow(rich_workflow)
        assert data["schema_version"] == 1
        assert data["name"] == "HRIS sync"
        assert data["requires"] == {"secrets": ["hris_token"]}
        assert "triggers" not in data

        refs = [node["ref"] for node in data["graph"]["nodes"]]
        assert refs == [
            "hook",
            "nightly",
            "on_incident",
            "fetch_employee",
            "gate",
            "end",
        ]
        dumped = yaml.dump(data)
        for node in data["graph"]["nodes"]:
            assert "id" not in node
        assert str(rich_workflow.id) not in dumped

        hook, nightly, incident = data["graph"]["nodes"][:3]
        assert hook["trigger_config"] == {"type": "webhook"}
        assert hook["input_mapping"] == {"employee_id": "data.id"}
        assert nightly["trigger_config"]["cron_expression"] == "0 2 * * *"
        assert incident["trigger_config"]["event_key"] == "incident.created"
        assert incident["trigger_config"]["filters"]["conditions"] == [
            {"field": "severity", "op": "lte", "value": "2"}
        ]

        # The condition node carries its routing branches inline; the default
        # is the is_default branch, and its conditions reference the variable
        # by key. No conditions travel on edges anymore.
        gate = data["graph"]["nodes"][4]
        assert gate["type"] == "condition"
        approved_branch, default_branch = gate["branches"]
        assert approved_branch["name"] == "approved"
        assert "is_default" not in approved_branch
        assert (
            approved_branch["condition_groups"][0]["conditions"][0]["variable"]
            == "approved"
        )
        assert default_branch["is_default"] is True
        assert "condition_groups" not in default_branch

        # Edges leaving the condition node reference their branch by index.
        gate_edges = [e for e in data["graph"]["edges"] if e["source"] == "gate"]
        assert {e["source_branch"] for e in gate_edges} == {"approved", "otherwise"}
        for edge in gate_edges:
            assert edge["target"] == "end"
            assert "condition_groups" not in edge

        fetch = data["graph"]["nodes"][3]
        assert fetch["retry"] == {
            "max_attempts": 3,
            "delay_seconds": 30,
            "backoff": "exponential",
        }
        assert "retry" not in hook

    def test_no_secrets_leak(self, rich_workflow):
        dumped = yaml.dump(export_workflow(rich_workflow))
        for registration in rich_workflow.triggers.all():
            assert registration.secret not in dumped
        assert "hmac-secret-value" not in dumped
        assert "hmac" not in dumped

    def test_requires_omitted_without_secret_references(self, db, root):
        workflow = Workflow.objects.create(name="Plain", folder=root)
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        _, payload = _rich_graph()
        payload["nodes"][3]["action_config"] = {"type": "log", "message": "hi"}
        save_graph(version, payload)
        assert "requires" not in export_workflow(workflow)


@pytest.mark.django_db
class TestImport:
    def test_roundtrip(self, rich_workflow, root):
        data = export_workflow(rich_workflow)
        imported, warnings = import_workflow(data, root)
        assert imported.id != rich_workflow.id
        assert imported.name == "HRIS sync (2)"
        draft = imported.draft_version
        assert draft is not None and draft.version_number == 1

        re_exported = export_workflow(imported)
        assert re_exported["graph"] == data["graph"]
        assert re_exported["requires"] == data["requires"]

    def test_import_creates_no_registrations_until_publish(self, rich_workflow, root):
        imported, _ = import_workflow(export_workflow(rich_workflow), root)
        assert imported.triggers.count() == 0

        imported.draft_version.publish(publisher_user())
        hook = imported.triggers.get(node_ref="hook")
        nightly = imported.triggers.get(node_ref="nightly")
        incident = imported.triggers.get(node_ref="on_incident")
        # Webhook arrives live with a FRESH secret; cron/event arrive disarmed.
        assert hook.enabled is True
        assert hook.secret != rich_workflow.triggers.get(node_ref="hook").secret
        assert hook.hmac_secret == ""
        assert nightly.enabled is False and nightly.next_run_at is None
        assert incident.enabled is False
        assert incident.event_key == "incident.created"

    def test_condition_variables_remapped(self, rich_workflow, root):
        imported, _ = import_workflow(export_workflow(rich_workflow), root)
        version = imported.draft_version
        approved = version.variables.get(key="approved")
        condition = approved.conditions.get()
        assert condition.value == "true"
        # ConditionGroup now hangs off a branch of a condition node, not an edge.
        assert condition.group.branch.node.version_id == version.id

    def test_falsy_condition_value_survives_import(self, root):
        """A boolean condition of `value: false` (or 0) must not collapse to ''
        on import — the operand would silently change (regression). Document
        shape uses refs/keys/branch-names, per the exchange format (D28)."""
        doc = {
            "schema_version": 1,
            "name": "Falsy",
            "graph": {
                "variables": [
                    {"key": "flag", "type": "boolean", "default_value": True}
                ],
                "nodes": [
                    {
                        "ref": "t",
                        "type": "trigger",
                        "trigger_config": {"type": "manual"},
                    },
                    {
                        "ref": "gate",
                        "type": "condition",
                        "label": "Gate",
                        "branches": [
                            {
                                "name": "off",
                                "condition_groups": [
                                    {
                                        "operator": "and",
                                        "conditions": [
                                            {
                                                "variable": "flag",
                                                "op": "eq",
                                                "value": False,
                                            }
                                        ],
                                        "children": [],
                                    }
                                ],
                            },
                            {
                                "name": "otherwise",
                                "is_default": True,
                                "condition_groups": [],
                            },
                        ],
                    },
                    {"ref": "end", "type": "end"},
                ],
                "edges": [
                    {"source": "t", "target": "gate"},
                    {"source": "gate", "target": "end", "source_branch": "off"},
                    {"source": "gate", "target": "end", "source_branch": "otherwise"},
                ],
            },
        }
        imported, _ = import_workflow(doc, root)
        condition = imported.draft_version.variables.get(key="flag").conditions.get()
        assert condition.value == "false"

    def test_missing_secret_warning(self, rich_workflow, root):
        _, warnings = import_workflow(export_workflow(rich_workflow), root)
        assert any("hris_token" in w and "Missing secrets" in w for w in warnings)

        # Secrets are workflow-scoped: the dialog value attaches to the new
        # workflow at import, so the warning no longer fires.
        _, warnings = import_workflow(
            export_workflow(rich_workflow), root, secrets={"hris_token": "x"}
        )
        assert not any("Missing secrets" in w for w in warnings)

    def test_publish_blocks_on_missing_secret(self, rich_workflow, root):
        from workflows.models import WorkflowSecret
        from workflows.validation import validate_graph

        imported, _ = import_workflow(export_workflow(rich_workflow), root)
        errors = validate_graph(imported.draft_version)
        missing = [e for e in errors if e["code"] == "secret_missing"]
        assert len(missing) == 1
        assert "hris_token" in missing[0]["message"]
        fetch = imported.draft_version.nodes.get(ref="fetch_employee")
        assert missing[0]["node_id"] == str(fetch.id)

        # The secret must live on the workflow itself, not merely its folder.
        WorkflowSecret.objects.create(workflow=imported, name="hris_token", value="x")
        errors = validate_graph(imported.draft_version)
        assert not any(e["code"] == "secret_missing" for e in errors)

    def test_task_template_resolution(self, rich_workflow, root):
        data = export_workflow(rich_workflow)
        data["graph"]["nodes"][3] = {
            "ref": "fetch_employee",
            "type": "task",
            "label": "Vendor review",
            "task_template": "Vendor review",
        }
        _, warnings = import_workflow(data, root)
        assert any("task template 'Vendor review'" in w for w in warnings)

        TaskTemplate.objects.create(name="Vendor review", folder=root)
        imported, warnings = import_workflow(data, root)
        node = imported.draft_version.nodes.get(ref="fetch_employee")
        assert node.task_template.name == "Vendor review"
        assert not any("task template" in w for w in warnings)

    def test_subprocess_resolution_excludes_self(self, rich_workflow, root):
        data = export_workflow(rich_workflow)
        data["name"] = "Caller"
        data["graph"]["nodes"][3] = {
            "ref": "fetch_employee",
            "type": "subprocess",
            "subprocess_workflow": "Caller",
        }
        _, warnings = import_workflow(data, root)
        assert any("subprocess workflow 'Caller'" in w for w in warnings)

        data["graph"]["nodes"][3]["subprocess_workflow"] = "HRIS sync"
        imported, _ = import_workflow(data, root)
        node = imported.draft_version.nodes.get(ref="fetch_employee")
        assert node.subprocess_workflow_id == rich_workflow.id

    def test_role_resolution(self, rich_workflow, root):
        from pmbok.models import ResponsibilityRole

        ResponsibilityRole.create_default_roles()
        data = export_workflow(rich_workflow)
        data["graph"]["nodes"][3]["assignments"] = [
            {"role": {"taxonomy": "raci", "code": "R"}},
            {"role": {"taxonomy": "raci", "code": "ZZ"}},
        ]
        imported, warnings = import_workflow(data, root)
        node = imported.draft_version.nodes.get(ref="fetch_employee")
        assignments = list(node.assignments.all())
        assert len(assignments) == 1
        assert assignments[0].role.code == "R"
        assert assignments[0].actor is None
        assert any("ZZ" in w for w in warnings)
        assert any("assignees are not exported" in w for w in warnings)

    def test_event_trigger_foreign_folder_filter_stripped(self, rich_workflow, root):
        sub = Folder.objects.create(
            name="Sub", parent_folder=root, content_type=Folder.ContentType.DOMAIN
        )
        foreign = str(uuid.uuid4())
        data = export_workflow(rich_workflow)
        incident = data["graph"]["nodes"][2]
        incident["trigger_config"]["filters"] = {
            "operator": "and",
            "conditions": [
                {"field": "folder", "op": "in", "value": f"{sub.id},{foreign}"},
                {"field": "severity", "op": "lte", "value": "2"},
            ],
        }
        imported, warnings = import_workflow(data, root)
        node = imported.draft_version.nodes.get(ref="on_incident")
        conditions = node.trigger_config["filters"]["conditions"]
        assert {"field": "folder", "op": "in", "value": str(sub.id)} in conditions
        assert any("folder filter" in w for w in warnings)

        incident["trigger_config"]["filters"] = {
            "operator": "and",
            "conditions": [{"field": "folder", "op": "eq", "value": foreign}],
        }
        imported, warnings = import_workflow(data, root)
        node = imported.draft_version.nodes.get(ref="on_incident")
        assert node.trigger_config["filters"] == {}

    def test_uuid_literal_warning(self, rich_workflow, root):
        data = export_workflow(rich_workflow)
        data["graph"]["nodes"][3]["action_config"] = {
            "type": "create_object",
            "model": "applied_control",
            "fields": {"name": "x", "folder": str(uuid.uuid4())},
        }
        _, warnings = import_workflow(data, root)
        assert any(
            "ids from the source instance" in w and "fetch_employee" in w
            for w in warnings
        )


def _condition_doc(name="Branchy"):
    """A portable doc with a condition node: trigger → route(low / else) →
    {action, end}. Branch order is list order; edges reference a branch by
    index. Used by the branch edge-case tests."""
    return {
        "schema_version": 1,
        "name": name,
        "graph": {
            "variables": [{"key": "lvl", "type": "string"}],
            "nodes": [
                {
                    "ref": "s",
                    "type": "trigger",
                    "trigger_config": {"type": "manual"},
                    "input_mapping": {"lvl": "data.lvl"},
                },
                {
                    "ref": "route",
                    "type": "condition",
                    "label": "Route",
                    "branches": [
                        {
                            "name": "low",
                            "condition_groups": [
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {"variable": "lvl", "op": "eq", "value": "low"}
                                    ],
                                }
                            ],
                        },
                        {"name": "else", "is_default": True},
                    ],
                },
                {"ref": "a", "type": "action", "action_config": {"type": "log"}},
                {"ref": "e", "type": "end"},
            ],
            "edges": [
                {"source": "s", "target": "route"},
                {"source": "route", "target": "a", "source_branch": 0},
                {"source": "route", "target": "e", "source_branch": 1},
                {"source": "a", "target": "e"},
            ],
        },
    }


@pytest.mark.django_db
class TestBranchEdgeCases:
    """Adversarial import/export shapes for the D25 node-owned branch model."""

    def _stable(self, data, root):
        """export∘import is idempotent: importing a doc then re-exporting, and
        importing that then re-exporting again, yields the same graph."""
        first, _ = import_workflow(data, root)
        doc2 = export_workflow(first)
        second, _ = import_workflow(doc2, root)
        doc3 = export_workflow(second)
        assert doc2["graph"] == doc3["graph"]
        return first, doc2

    def test_single_condition_round_trips(self, root):
        wf, doc = self._stable(_condition_doc(), root)
        gate = next(n for n in doc["graph"]["nodes"] if n["type"] == "condition")
        assert [b.get("is_default") for b in gate["branches"]] == [None, True]

    def test_two_condition_nodes_have_per_node_indices(self, root):
        # The risky case: source_branch is an index WITHIN the source node's
        # branch list, so two condition nodes must not cross-resolve.
        doc = {
            "schema_version": 1,
            "name": "TwoConds",
            "graph": {
                "variables": [{"key": "k", "type": "string"}],
                "nodes": [
                    {
                        "ref": "s",
                        "type": "trigger",
                        "trigger_config": {"type": "manual"},
                    },
                    {
                        "ref": "c1",
                        "type": "condition",
                        "branches": [
                            {
                                "name": "p",
                                "condition_groups": [
                                    {
                                        "conditions": [
                                            {"variable": "k", "op": "eq", "value": "p"}
                                        ]
                                    }
                                ],
                            },
                            {"name": "pd", "is_default": True},
                        ],
                    },
                    {
                        "ref": "c2",
                        "type": "condition",
                        "branches": [
                            {
                                "name": "q",
                                "condition_groups": [
                                    {
                                        "conditions": [
                                            {"variable": "k", "op": "eq", "value": "q"}
                                        ]
                                    }
                                ],
                            },
                            {"name": "qd", "is_default": True},
                        ],
                    },
                    {"ref": "x", "type": "action", "action_config": {"type": "log"}},
                    {"ref": "e", "type": "end"},
                ],
                "edges": [
                    {"source": "s", "target": "c1"},
                    {"source": "c1", "target": "c2", "source_branch": 0},
                    {"source": "c1", "target": "x", "source_branch": 1},
                    {"source": "c2", "target": "x", "source_branch": 0},
                    {"source": "c2", "target": "x", "source_branch": 1},
                    {"source": "x", "target": "e"},
                ],
            },
        }
        workflow, _ = self._stable(doc, root)
        version = workflow.draft_version
        c2 = version.nodes.get(ref="c2")
        # Every edge leaving c2 must wire to a branch that belongs to c2.
        for edge in version.edges.filter(source_node=c2):
            assert edge.source_branch is not None
            assert edge.source_branch.node_id == c2.id
        assert sorted(b.name for b in c2.branches.all()) == ["q", "qd"]

    def test_nested_condition_tree_round_trips(self, root):
        data = _condition_doc("Nested")
        data["graph"]["variables"].append({"key": "b", "type": "string"})
        data["graph"]["nodes"][1]["branches"][0]["condition_groups"] = [
            {
                "operator": "and",
                "conditions": [{"variable": "lvl", "op": "eq", "value": "x"}],
                "children": [
                    {
                        "operator": "or",
                        "conditions": [
                            {"variable": "b", "op": "eq", "value": "y"},
                            {"variable": "b", "op": "eq", "value": "z"},
                        ],
                    }
                ],
            }
        ]
        workflow, _ = self._stable(data, root)
        branch = workflow.draft_version.nodes.get(ref="route").branches.get(name="low")
        assert branch.condition_groups.filter(parent_group__isnull=True).count() == 1
        assert branch.condition_groups.filter(parent_group__isnull=False).count() == 1

    def test_unwired_branch_round_trips(self, root):
        # A branch with no edge (draft state) must survive export/import intact.
        data = _condition_doc("Unwired")
        data["graph"]["nodes"][1]["branches"].insert(
            1, {"name": "orphan"}
        )  # no edge references index 1
        # shift the default edge's index (default is now at index 2)
        for edge in data["graph"]["edges"]:
            if edge.get("source_branch") == 1:
                edge["source_branch"] = 2
        workflow, doc = self._stable(data, root)
        route = workflow.draft_version.nodes.get(ref="route")
        assert route.branches.count() == 3
        assert not route.branches.get(name="orphan").edges.exists()

    def test_only_default_condition_node_round_trips(self, root):
        data = _condition_doc("OnlyDefault")
        data["graph"]["nodes"][1]["branches"] = [{"name": "always", "is_default": True}]
        data["graph"]["edges"] = [
            {"source": "s", "target": "route"},
            {"source": "route", "target": "e", "source_branch": 0},
        ]
        data["graph"]["nodes"][2:3] = []  # drop the now-unused action node
        workflow, _ = self._stable(data, root)
        route = workflow.draft_version.nodes.get(ref="route")
        assert route.branches.count() == 1
        assert route.branches.first().is_default is True


@pytest.mark.django_db
class TestImportRejections:
    def _base(self):
        return {
            "schema_version": 1,
            "name": "Broken",
            "graph": {
                "variables": [],
                "nodes": [
                    {
                        "ref": "go",
                        "type": "trigger",
                        "trigger_config": {"type": "manual"},
                    }
                ],
                "edges": [],
            },
        }

    def test_not_a_mapping(self, root):
        with pytest.raises(WorkflowImportError):
            import_workflow(["nope"], root)

    def test_wrong_schema_version(self, root):
        data = self._base()
        data["schema_version"] = 99
        with pytest.raises(WorkflowImportError, match="schema_version"):
            import_workflow(data, root)

    def test_missing_name(self, root):
        data = self._base()
        data["name"] = "  "
        with pytest.raises(WorkflowImportError, match="name"):
            import_workflow(data, root)

    def test_invalid_ref(self, root):
        data = self._base()
        data["graph"]["nodes"][0]["ref"] = "Bad Ref!"
        with pytest.raises(WorkflowImportError, match="ref"):
            import_workflow(data, root)

    def test_duplicate_refs(self, root):
        data = self._base()
        data["graph"]["nodes"].append({"ref": "go", "type": "end"})
        with pytest.raises(WorkflowImportError, match="Duplicate node ref"):
            import_workflow(data, root)

    def test_unknown_node_type(self, root):
        data = self._base()
        data["graph"]["nodes"][0]["type"] = "teleport"
        with pytest.raises(WorkflowImportError, match="unknown type"):
            import_workflow(data, root)

    def test_legacy_start_node_gets_specific_hint(self, root):
        data = self._base()
        data["graph"]["nodes"][0]["type"] = "start"
        with pytest.raises(WorkflowImportError, match="predates trigger nodes"):
            import_workflow(data, root)

    def test_edge_to_unknown_ref(self, root):
        data = self._base()
        data["graph"]["edges"] = [{"source": "go", "target": "ghost"}]
        with pytest.raises(WorkflowImportError, match="ghost"):
            import_workflow(data, root)

    def test_condition_on_unknown_variable(self, root):
        data = self._base()
        data["graph"]["nodes"].append(
            {
                "ref": "gate",
                "type": "condition",
                "branches": [
                    {
                        "name": "x",
                        "condition_groups": [
                            {"conditions": [{"variable": "ghost", "op": "eq"}]}
                        ],
                    }
                ],
            }
        )
        data["graph"]["nodes"].append({"ref": "end", "type": "end"})
        data["graph"]["edges"] = [
            {"source": "go", "target": "gate"},
            {"source": "gate", "target": "end", "source_branch": 0},
        ]
        with pytest.raises(WorkflowImportError, match="unknown variable"):
            import_workflow(data, root)

    def test_source_branch_index_out_of_range(self, root):
        data = _condition_doc()
        for edge in data["graph"]["edges"]:
            if edge.get("source_branch") is not None:
                edge["source_branch"] = 9
        with pytest.raises(WorkflowImportError, match="branch"):
            import_workflow(data, root)

    def test_source_branch_on_non_condition_edge(self, root):
        data = _condition_doc()
        for edge in data["graph"]["edges"]:
            if edge["source"] == "s":  # trigger → condition, not a branch edge
                edge["source_branch"] = 0
        with pytest.raises(WorkflowImportError, match="source_branch"):
            import_workflow(data, root)

    def test_condition_edge_without_source_branch(self, root):
        data = _condition_doc()
        for edge in data["graph"]["edges"]:
            if edge["source"] == "route":
                edge.pop("source_branch", None)
        with pytest.raises(WorkflowImportError, match="source_branch"):
            import_workflow(data, root)

    def test_duplicate_variable_keys_rejected_atomically(self, root):
        data = self._base()
        data["graph"]["variables"] = [
            {"key": "x", "type": "string"},
            {"key": "x", "type": "number"},
        ]
        before = Workflow.objects.count()
        with pytest.raises(WorkflowImportError, match="Duplicate variable key"):
            import_workflow(data, root)
        assert Workflow.objects.count() == before

    def test_workflow_name_collision_suffixed(self, root):
        data = self._base()
        first, warnings_first = import_workflow(data, root)
        assert first.name == "Broken"
        assert warnings_first == []
        second, warnings = import_workflow(data, root)
        assert second.name == "Broken (2)"
        assert any("already exists" in w for w in warnings)


@pytest.mark.django_db
class TestApi:
    def _export(self, workflow, user):
        factory = APIRequestFactory()
        view = WorkflowViewSet.as_view({"get": "export_yaml"})
        req = factory.get(f"/api/workflows/workflows/{workflow.id}/export-yaml/")
        force_authenticate(req, user=user)
        return view(req, pk=str(workflow.id))

    def _import(self, content, user, folder=None, filename="wf.yaml", secrets=None):
        from django.core.files.uploadedfile import SimpleUploadedFile

        factory = APIRequestFactory()
        view = WorkflowViewSet.as_view({"post": "import_yaml"})
        data = {"file": SimpleUploadedFile(filename, content)}
        if folder:
            data["folder"] = str(folder.id)
        if secrets is not None:
            import json

            data["secrets"] = json.dumps(secrets)
        req = factory.post(
            "/api/workflows/workflows/import-yaml/", data, format="multipart"
        )
        force_authenticate(req, user=user)
        return view(req)

    def test_export_endpoint(self, rich_workflow, superuser):
        resp = self._export(rich_workflow, superuser)
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/x-yaml"
        assert 'attachment; filename="hris-sync.yaml"' in resp["Content-Disposition"]
        data = yaml.safe_load(resp.content)
        assert data["name"] == "HRIS sync"

    def test_import_endpoint_roundtrip(self, rich_workflow, superuser, root):
        exported = self._export(rich_workflow, superuser).content
        resp = self._import(exported, superuser, folder=root)
        assert resp.status_code == 201, resp.data
        assert resp.data["name"] == "HRIS sync (2)"
        assert isinstance(resp.data["warnings"], list)
        assert Workflow.objects.filter(id=resp.data["id"]).exists()

    def test_import_with_provided_secrets(self, rich_workflow, superuser, root):
        from workflows.models import WorkflowSecret

        exported = self._export(rich_workflow, superuser).content
        resp = self._import(
            exported,
            superuser,
            folder=root,
            secrets={"hris_token": "tok-123", "": "junk", "unrelated": ""},
        )
        assert resp.status_code == 201, resp.data
        # Secret is attached to the imported workflow (folder propagated from it).
        secret = WorkflowSecret.objects.get(
            workflow_id=resp.data["id"], name="hris_token"
        )
        assert secret.value == "tok-123"
        assert secret.folder_id == root.id
        assert not WorkflowSecret.objects.filter(name="unrelated").exists()
        assert not any("Missing secrets" in w for w in resp.data["warnings"])

    def test_import_invalid_yaml(self, superuser):
        resp = self._import(b"{unbalanced: [", superuser)
        assert resp.status_code == 400
        assert resp.data["error"] == "invalidYamlFile"

    def test_import_no_file(self, superuser):
        factory = APIRequestFactory()
        view = WorkflowViewSet.as_view({"post": "import_yaml"})
        req = factory.post("/api/workflows/workflows/import-yaml/", {})
        force_authenticate(req, user=superuser)
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["error"] == "noFileProvided"

    def test_import_too_large(self, superuser):
        resp = self._import(b"a" * (1024 * 1024 + 1), superuser)
        assert resp.status_code == 400
        assert resp.data["error"] == "fileTooLarge"

    def test_import_requires_add_workflow(self, rich_workflow, superuser, db):
        exported = self._export(rich_workflow, superuser).content
        plain = User.objects.create_user(email="workflow_ie_plain@example.com")
        resp = self._import(exported, plain)
        assert resp.status_code == 403
