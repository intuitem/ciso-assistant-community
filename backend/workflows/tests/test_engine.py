import uuid

import pytest
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from core.models import AppliedControl
from iam.models import Folder, User, UserGroup
from workflows.engine import broadcast_event, start_instance
from workflows.graph import save_graph
from workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowToken,
    WorkflowVersion,
)
from workflows.views import WorkflowInstanceViewSet, WorkflowTokenViewSet


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(email="engine_test@example.com", password="x")


def make_workflow(name="Test flow", folder=None):
    workflow = Workflow.objects.create(
        name=name, folder=folder or Folder.get_root_folder()
    )
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

    def test_parallel_fan_out_runs_converging_node_per_token(self):
        # Fan-out is always parallel; without a merge node (spec D30) a
        # converging node runs once per arriving token.
        _, version = make_workflow()
        start = node("trigger", trigger_config={"type": "manual"})
        fork = node("action", label="Fork", action_config={"type": "log"})
        branch_a = node("action", label="A", action_config={"type": "log"})
        branch_b = node("action", label="B", action_config={"type": "log"})
        converge = node("action", label="Converge", action_config={"type": "log"})
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, fork, branch_a, branch_b, converge, end],
                "edges": [
                    edge(start, fork),
                    edge(fork, branch_a),
                    edge(fork, branch_b),
                    edge(branch_a, converge),
                    edge(branch_b, converge),
                    edge(converge, end),
                ],
                "variables": [],
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        entered = instance.logs.filter(
            event_type="node_entered", node__label="Converge"
        ).count()
        assert entered == 2

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


@pytest.mark.django_db
class TestSubprocess:
    def _publish_child(self, *, event_key=None, failing=False):
        child_wf = Workflow.objects.create(
            name=f"Child {uuid.uuid4()}", folder=Folder.get_root_folder()
        )
        cv = WorkflowVersion.objects.create(workflow=child_wf)
        chain = [node("trigger", trigger_config={"type": "manual"})]
        if event_key:
            chain.append(node("event", event_key=event_key))
        if failing:
            chain.append(
                node(
                    "action",
                    action_config={
                        "type": "create_object",
                        "model": "nonexistent_model",
                        "fields": {"name": "x"},
                    },
                )
            )
        else:
            chain.append(
                node(
                    "action",
                    action_config={
                        "type": "set_variables",
                        "variables": {"result": "done"},
                    },
                )
            )
        chain.append(node("end"))
        edges = [edge(chain[i], chain[i + 1]) for i in range(len(chain) - 1)]
        save_graph(cv, {"nodes": chain, "edges": edges, "variables": []})
        cv.publish()
        return child_wf

    def _parent(self, child_wf, output_mapping=None):
        _, pv = make_workflow("Parent")
        trig = node("trigger", trigger_config={"type": "manual"})
        sub = node(
            "subprocess",
            label="Run child",
            subprocess_workflow=str(child_wf.id),
            output_mapping=output_mapping or {},
        )
        end = node("end")
        save_graph(
            pv,
            {
                "nodes": [trig, sub, end],
                "edges": [edge(trig, sub), edge(sub, end)],
                "variables": [],
            },
        )
        return pv, sub

    def test_sync_completion_stores_node_output(self):
        child = self._publish_child()
        pv, sub = self._parent(child, output_mapping={"child_result": "result"})
        instance = start_instance(pv)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        ref = pv.nodes.get(id=sub["id"]).ref
        assert instance.node_outputs[ref]["result"] == "done"
        assert instance.variables["child_result"] == "done"

    def test_async_completion_hands_back_output(self):
        child = self._publish_child(event_key="go")
        pv, sub = self._parent(child, output_mapping={"child_result": "result"})
        instance = start_instance(pv)
        # Child parked on its event node, so the parent's subprocess token
        # parks too (the trigger token is already consumed).
        assert instance.status == WorkflowInstance.Status.ACTIVE
        assert instance.tokens.filter(status=WorkflowToken.Status.WAITING).count() == 1
        child_instance = WorkflowInstance.objects.get(parent_instance=instance)
        assert child_instance.status == WorkflowInstance.Status.ACTIVE
        # Waking the child drives it to completion, which must hand the output
        # back to the waiting parent (regression: node output was dropped).
        broadcast_event("go", instance)
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.COMPLETED
        ref = pv.nodes.get(id=sub["id"]).ref
        assert instance.node_outputs[ref]["result"] == "done"
        assert instance.variables["child_result"] == "done"

    def test_async_failure_propagates_to_parent(self):
        child = self._publish_child(event_key="go", failing=True)
        pv, _ = self._parent(child)
        instance = start_instance(pv)
        assert instance.status == WorkflowInstance.Status.ACTIVE
        # A failing child must fail the parent, not leave it waiting forever.
        broadcast_event("go", instance)
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.FAILED
        assert not instance.tokens.filter(status=WorkflowToken.Status.WAITING).exists()

    def _wire_subprocess(self, version, target_workflow):
        start = node("trigger", trigger_config={"type": "manual"})
        sub = node("subprocess", subprocess_workflow=str(target_workflow.id))
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, sub, end],
                "edges": [edge(start, sub), edge(sub, end)],
                "variables": [],
            },
        )

    def test_self_reference_fails_publish(self):
        from workflows.validation import validate_graph

        workflow, version = make_workflow("Selfie")
        self._wire_subprocess(version, workflow)
        codes = [e["code"] for e in validate_graph(version)]
        assert "subprocess_self_reference" in codes

    def test_cross_workflow_cycle_capped_at_runtime(self):
        # A -> B -> A -> ... dodges the publish-time self-reference check, so
        # the runtime depth cap must stop it instead of recursing unbounded.
        a_wf, a_v = make_workflow("Cycle A")
        b_wf, b_v = make_workflow("Cycle B")
        self._wire_subprocess(a_v, b_wf)
        self._wire_subprocess(b_v, a_wf)
        a_v.publish()
        b_v.publish()
        instance = start_instance(a_wf.published_version)
        assert instance.status == WorkflowInstance.Status.FAILED
        # The depth cap (not a Python RecursionError) terminated it: the
        # deepest instance logs "too deep"; the outer ones log "Subprocess
        # failed", so check across all instances.
        from workflows.models import WorkflowInstanceLog

        assert WorkflowInstanceLog.objects.filter(
            event_type="error", message__icontains="too deep"
        ).exists()


@pytest.mark.django_db
class TestTokenAdmin:
    """Operator recovery endpoints for stuck runs (spec D10)."""

    def _errored_instance(self):
        _, version = make_workflow()
        start = node("trigger", trigger_config={"type": "manual"})
        bad = node(
            "action",
            label="Bad",
            action_config={
                "type": "create_object",
                "model": "nonexistent_model",
                "fields": {"name": "x"},
            },
        )
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
        token = instance.tokens.get(status=WorkflowToken.Status.ERROR)
        return instance, token

    def _post(self, token, action_name, user):
        factory = APIRequestFactory()
        view = WorkflowTokenViewSet.as_view({"post": action_name})
        req = factory.post(f"/api/workflows/workflow-tokens/{token.id}/{action_name}/")
        force_authenticate(req, user=user)
        return view(req, pk=str(token.id))

    def test_skip_advances_to_completion(self, superuser):
        instance, token = self._errored_instance()
        resp = self._post(token, "skip", superuser)
        assert resp.status_code == 200, resp.data
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.COMPLETED

    def test_abort_marks_abandoned(self, superuser):
        instance, token = self._errored_instance()
        resp = self._post(token, "abort", superuser)
        assert resp.status_code == 200, resp.data
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.ABANDONED
        assert not instance.tokens.exclude(
            status=WorkflowToken.Status.CONSUMED
        ).exists()

    def test_retry_reruns_the_node(self, superuser, monkeypatch):
        _, version = make_workflow()
        calls = {"n": 0}

        class Resp:
            is_redirect = False
            next = None

            def __init__(self, code):
                self.status_code = code

            def json(self):
                return {"ok": True}

        def flaky(method, url, **kw):
            calls["n"] += 1
            return Resp(500 if calls["n"] == 1 else 200)

        monkeypatch.setattr("requests.request", flaky)
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda u, **k: None
        )
        start = node("trigger", trigger_config={"type": "manual"})
        act = node(
            "action",
            action_config={"type": "http_request", "url": "https://api.example.com/x"},
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, act, end],
                "edges": [edge(start, act), edge(act, end)],
                "variables": [],
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        token = instance.tokens.get(status=WorkflowToken.Status.ERROR)
        resp = self._post(token, "retry", superuser)
        assert resp.status_code == 200, resp.data
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert calls["n"] == 2


@pytest.mark.django_db
class TestManualRunAuthz:
    """Manual-run endpoint must be folder-scoped and reject stale versions."""

    def _publish_in(self, folder):
        workflow, version = make_workflow("Runnable", folder=folder)
        start = node("trigger", trigger_config={"type": "manual"})
        log = node("action", action_config={"type": "log", "message": "hi"})
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, log, end],
                "edges": [edge(start, log), edge(log, end)],
                "variables": [],
            },
        )
        version.publish()
        return workflow

    def _post(self, version_id, user):
        factory = APIRequestFactory()
        view = WorkflowInstanceViewSet.as_view({"post": "create"})
        req = factory.post(
            "/api/workflows/workflow-instances/",
            {"version": version_id},
            format="json",
        )
        force_authenticate(req, user=user)
        return view(req)

    def test_unprivileged_user_forbidden(self):
        workflow = self._publish_in(Folder.get_root_folder())
        user = User.objects.create_user(email="nobody@example.com")
        resp = self._post(str(workflow.published_version.id), user)
        assert resp.status_code == 403

    def test_view_only_analyst_cannot_run_in_their_domain(self):
        domain = Folder.objects.create(
            name="Run domain",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
            create_iam_groups=True,
        )
        Folder.create_default_ug_and_ra(domain)
        workflow = self._publish_in(domain)
        analyst = User.objects.create_user(email="ana@example.com")
        analyst.user_groups.add(UserGroup.objects.get(folder=domain, name="BI-UG-ANA"))
        resp = self._post(str(workflow.published_version.id), analyst)
        assert resp.status_code == 403

    def test_archived_version_rejected(self, superuser):
        workflow = self._publish_in(Folder.get_root_folder())
        version = workflow.published_version
        version.status = WorkflowVersion.Status.ARCHIVED
        version.save(update_fields=["status"])
        resp = self._post(str(version.id), superuser)
        assert resp.status_code == 400
        assert resp.data["error"] == "onlyCurrentVersionsCanBeRun"

    def test_stale_draft_rejected(self, superuser):
        workflow, stale = make_workflow("Multiple drafts")
        current = WorkflowVersion.objects.create(
            workflow=workflow,
            version_number=stale.version_number + 1,
        )
        assert workflow.draft_version == current
        resp = self._post(str(stale.id), superuser)
        assert resp.status_code == 400
        assert resp.data["error"] == "onlyCurrentVersionsCanBeRun"


@pytest.mark.django_db
class TestTemplatedConditionOperators:
    """in/not_in/contains must compare against the RENDERED value, not the
    literal '{{...}}' string (regression)."""

    def _route(self, op, value, payload):
        # Unique name: a test calls this twice and workflow names are unique
        # per folder.
        _, version = make_workflow(f"Route {uuid.uuid4()}")
        subject = str(uuid.uuid4())
        needle = str(uuid.uuid4())
        match_branch = str(uuid.uuid4())
        default_branch = str(uuid.uuid4())
        start = node(
            "trigger",
            trigger_config={"type": "manual"},
            input_mapping={"subject": "subject", "needle": "needle"},
        )
        gate = node(
            "condition",
            label="Gate",
            branches=[
                {
                    "id": match_branch,
                    "name": "match",
                    "order": 0,
                    "is_default": False,
                    "condition_groups": [
                        {
                            "operator": "and",
                            "conditions": [
                                {"variable": subject, "op": op, "value": value}
                            ],
                            "children": [],
                        }
                    ],
                },
                {
                    "id": default_branch,
                    "name": "other",
                    "order": 1,
                    "is_default": True,
                    "condition_groups": [],
                },
            ],
        )
        matched = node(
            "action",
            label="M",
            action_config={"type": "set_variables", "variables": {"result": "matched"}},
        )
        other = node(
            "action",
            label="O",
            action_config={"type": "set_variables", "variables": {"result": "default"}},
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, gate, matched, other, end],
                "edges": [
                    edge(start, gate),
                    edge(gate, matched, source_branch=match_branch),
                    edge(gate, other, source_branch=default_branch),
                    edge(matched, end),
                    edge(other, end),
                ],
                "variables": [
                    {"id": subject, "key": "subject", "type": "string"},
                    {"id": needle, "key": "needle", "type": "string"},
                ],
            },
        )
        instance = start_instance(version, payload=payload)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        return instance.variables.get("result")

    def test_contains_uses_templated_value(self):
        # Pre-fix, contains compared "hello world" against the literal
        # "{{needle}}" and fell through to default.
        assert (
            self._route(
                "contains", "{{needle}}", {"subject": "hello world", "needle": "world"}
            )
            == "matched"
        )
        assert (
            self._route(
                "contains", "{{needle}}", {"subject": "hello world", "needle": "zzz"}
            )
            == "default"
        )

    def test_in_uses_templated_value(self):
        assert (
            self._route("in", "{{needle}}", {"subject": "b", "needle": "a,b,c"})
            == "matched"
        )
        assert (
            self._route("in", "{{needle}}", {"subject": "x", "needle": "a,b,c"})
            == "default"
        )

    def test_not_in_uses_templated_value(self):
        assert (
            self._route("not_in", "{{needle}}", {"subject": "x", "needle": "a,b,c"})
            == "matched"
        )
        assert (
            self._route("not_in", "{{needle}}", {"subject": "b", "needle": "a,b,c"})
            == "default"
        )
