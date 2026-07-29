import uuid

import pytest
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from core.models import AppliedControl
from iam.models import Folder, User
from workflows.engine import start_instance
from workflows.graph import save_graph
from workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowToken,
    WorkflowVersion,
)
from workflows.views import WorkflowInstanceViewSet


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(email="engine_test@example.com", password="x")


def make_workflow(name="Test flow"):
    workflow = Workflow.objects.create(name=name, folder=Folder.get_root_folder())
    version = WorkflowVersion.objects.create(workflow=workflow)
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
class TestLinearExecution:
    def test_action_flow_completes(self):
        _, version = make_workflow()
        start = node("trigger", trigger_config={"type": "manual"})
        log = node(
            "action", label="Log", action_config={"type": "log", "message": "hi"}
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, log, end],
                "edges": [edge(start, log), edge(log, end)],
                "variables": [],
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        events = list(instance.logs.values_list("event_type", flat=True))
        assert "action_executed" in events
        assert "instance_completed" in events

    def test_create_object_with_templating(self):
        _, version = make_workflow()
        var_id = str(uuid.uuid4())
        start = node(
            "trigger",
            trigger_config={"type": "manual"},
            input_mapping={"vendor_name": "vendor.name"},
        )
        create = node(
            "action",
            label="Create control",
            action_config={
                "type": "create_object",
                "model": "applied_control",
                "fields": {
                    "name": "Assess {{vendor_name}}",
                    "description": "From {{payload.source}}",
                },
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, create, end],
                "edges": [edge(start, create), edge(create, end)],
                "variables": [{"id": var_id, "key": "vendor_name", "type": "string"}],
            },
        )
        instance = start_instance(
            version, payload={"vendor": {"name": "Acme"}, "source": "n8n"}
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED
        control = AppliedControl.objects.get(name="Assess Acme")
        assert control.description == "From n8n"
        assert control.folder_id == instance.folder_id

    def test_create_incident_with_payload_severity(self):
        from core.models import Incident

        _, version = make_workflow()
        start = node(
            "trigger",
            trigger_config={"type": "manual"},
            input_mapping={"title": "alert.title", "sev": "alert.severity"},
        )
        create = node(
            "action",
            action_config={
                "type": "create_object",
                "model": "incident",
                "fields": {"name": "{{title}}", "severity": "{{sev}}"},
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, create, end],
                "edges": [edge(start, create), edge(create, end)],
                "variables": [],
            },
        )
        instance = start_instance(
            version, payload={"alert": {"title": "Suspicious login", "severity": 4}}
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, list(
            instance.logs.values_list("message", flat=True)
        )
        assert Incident.objects.filter(name="Suspicious login").exists()

    def test_fk_chaining_entity_then_assessment(self):
        from tprm.models import Entity, EntityAssessment

        _, version = make_workflow()
        start = node(
            "trigger",
            trigger_config={"type": "manual"},
            input_mapping={"vendor_name": "vendor"},
        )
        create_entity = node(
            "action",
            action_config={
                "type": "create_object",
                "model": "entity",
                "fields": {"name": "{{vendor_name}}"},
            },
            output_mapping={"entity_id": "created_object_id"},
        )
        create_assessment = node(
            "action",
            action_config={
                "type": "create_object",
                "model": "entity_assessment",
                "fields": {
                    "name": "Assessment — {{vendor_name}}",
                    "entity": "{{entity_id}}",
                },
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, create_entity, create_assessment, end],
                "edges": [
                    edge(start, create_entity),
                    edge(create_entity, create_assessment),
                    edge(create_assessment, end),
                ],
                "variables": [],
            },
        )
        instance = start_instance(version, payload={"vendor": "Initech"})
        assert instance.status == WorkflowInstance.Status.COMPLETED, list(
            instance.logs.values_list("message", flat=True)
        )
        entity = Entity.objects.get(name="Initech")
        assessment = EntityAssessment.objects.get(name="Assessment — Initech")
        assert assessment.entity_id == entity.id

    def test_fk_outside_folder_scope_is_rejected(self):
        from tprm.models import Entity

        _, version = make_workflow()
        sibling = Folder.objects.create(
            name="Sibling domain",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        # Workflow runs in a domain; the entity lives in a sibling domain.
        domain = Folder.objects.create(
            name="Workflow domain",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        version.workflow.folder = domain
        version.workflow.save()
        version.refresh_from_db()
        foreign_entity = Entity.objects.create(name="Foreign vendor", folder=sibling)

        start = node("trigger", trigger_config={"type": "manual"})
        create = node(
            "action",
            action_config={
                "type": "create_object",
                "model": "entity_assessment",
                "fields": {"name": "Sneaky", "entity": str(foreign_entity.id)},
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, create, end],
                "edges": [edge(start, create), edge(create, end)],
                "variables": [],
            },
        )
        instance = start_instance(version)
        assert instance.folder_id == domain.id
        assert instance.status == WorkflowInstance.Status.FAILED
        error = instance.tokens.get(status=WorkflowToken.Status.ERROR)
        assert "scope" in error.error_message

    def test_unknown_action_fails_token_not_request(self):
        _, version = make_workflow()
        start = node("trigger", trigger_config={"type": "manual"})
        bad = node("action", action_config={"type": "nope"})
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, bad, end],
                "edges": [edge(start, bad), edge(bad, end)],
                "variables": [],
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert instance.tokens.filter(status=WorkflowToken.Status.ERROR).exists()


@pytest.mark.django_db
class TestRouting:
    def _decision_version(self):
        _, version = make_workflow()
        var_id = str(uuid.uuid4())
        approved_branch = str(uuid.uuid4())
        default_branch = str(uuid.uuid4())
        start = node(
            "trigger",
            trigger_config={"type": "manual"},
            input_mapping={"decision": "decision"},
        )
        gate = node(
            "condition",
            label="Gate",
            branches=[
                {
                    "id": approved_branch,
                    "name": "approved",
                    "order": 0,
                    "is_default": False,
                    "condition_groups": [
                        {
                            "operator": "and",
                            "conditions": [
                                {"variable": var_id, "op": "eq", "value": "approved"}
                            ],
                            "children": [],
                        }
                    ],
                },
                {
                    "id": default_branch,
                    "name": "rejected",
                    "order": 1,
                    "is_default": True,
                    "condition_groups": [],
                },
            ],
        )
        approved = node("action", label="A", action_config={"type": "log"})
        rejected = node("action", label="R", action_config={"type": "log"})
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, gate, approved, rejected, end],
                "edges": [
                    edge(start, gate),
                    edge(gate, approved, source_branch=approved_branch),
                    edge(gate, rejected, source_branch=default_branch),
                    edge(approved, end),
                    edge(rejected, end),
                ],
                "variables": [{"id": var_id, "key": "decision", "type": "string"}],
            },
        )
        return version, approved["id"], rejected["id"]

    def test_condition_routes_matching_branch(self):
        version, approved_id, _ = self._decision_version()
        instance = start_instance(version, payload={"decision": "approved"})
        assert instance.status == WorkflowInstance.Status.COMPLETED
        visited = {str(t.current_node_id) for t in instance.tokens.all()}
        assert approved_id in visited

    def test_condition_falls_through_to_default_branch(self):
        version, approved_id, rejected_id = self._decision_version()
        instance = start_instance(version, payload={"decision": "nope"})
        visited = {str(t.current_node_id) for t in instance.tokens.all()}
        assert rejected_id in visited
        assert approved_id not in visited

    def test_parallel_fork_and_join(self):
        _, version = make_workflow()
        start = node("trigger", trigger_config={"type": "manual"})
        fork = node("action", label="Fork", action_config={"type": "log"})
        branch_a = node("action", label="A", action_config={"type": "log"})
        branch_b = node("action", label="B", action_config={"type": "log"})
        join = node(
            "action", label="Join", action_config={"type": "log"}, join_type="and"
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, fork, branch_a, branch_b, join, end],
                "edges": [
                    edge(start, fork),
                    edge(fork, branch_a),
                    edge(fork, branch_b),
                    edge(branch_a, join),
                    edge(branch_b, join),
                    edge(join, end),
                ],
                "variables": [],
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        fired = instance.logs.filter(event_type="join_fired")
        assert fired.count() == 1

    def test_task_node_parks_the_run(self):
        _, version = make_workflow()
        start = node("trigger", trigger_config={"type": "manual"})
        task = node("task", label="Human step")
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, task, end],
                "edges": [edge(start, task), edge(task, end)],
                "variables": [],
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.ACTIVE
        assert instance.tokens.filter(status=WorkflowToken.Status.WAITING).count() == 1


@pytest.mark.django_db
class TestTriggers:
    def _published_hook_version(self):
        workflow, version = make_workflow("Hooked")
        start = node(
            "trigger",
            ref="hook",
            trigger_config={"type": "webhook"},
            input_mapping={"vendor_name": "vendor.name"},
        )
        create = node(
            "action",
            action_config={
                "type": "create_object",
                "model": "applied_control",
                "fields": {"name": "Onboard {{vendor_name}}"},
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, create, end],
                "edges": [edge(start, create), edge(create, end)],
                "variables": [],
            },
        )
        version.publish()
        return workflow

    def test_webhook_trigger(self):
        workflow = self._published_hook_version()
        client = APIClient()
        secret = workflow.triggers.get(node_ref="hook").secret
        url = f"/api/workflows/hooks/{workflow.id}/hook/{secret}/"
        resp = client.post(url, {"vendor": {"name": "Umbrella"}}, format="json")
        assert resp.status_code == 201, resp.data
        assert resp.data["status"] == "completed"
        assert AppliedControl.objects.filter(name="Onboard Umbrella").exists()

    def test_webhook_bad_secret_404s(self):
        workflow = self._published_hook_version()
        client = APIClient()
        resp = client.post(
            f"/api/workflows/hooks/{workflow.id}/hook/wrong-secret/",
            {},
            format="json",
        )
        assert resp.status_code == 404

    def test_manual_run_endpoint(self, superuser):
        workflow = self._published_hook_version()
        version = workflow.published_version
        factory = APIRequestFactory()
        view = WorkflowInstanceViewSet.as_view({"post": "create"})
        req = factory.post(
            "/api/workflows/workflow-instances/",
            {"version": str(version.id)},
            format="json",
        )
        force_authenticate(req, user=superuser)
        resp = view(req)
        assert resp.status_code == 201, resp.data
        assert resp.data["trigger"] == "manual"
