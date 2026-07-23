import uuid

import pytest
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from core.models import AppliedControl
from iam.models import Folder, User, UserGroup
from workflows.engine import start_instance
from workflows.graph import save_graph
from workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowSecret,
    WorkflowToken,
    WorkflowVersion,
)
from workflows.views import WorkflowVersionViewSet


def make_workflow(name="Integration flow", folder=None):
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


def linear_graph(version, *action_configs, node_extras=None, trigger=None):
    start = node("trigger", **(trigger or {"trigger_config": {"type": "manual"}}))
    actions = [
        node(
            "action",
            action_config=config,
            **(node_extras or [{}] * len(action_configs))[i],
        )
        for i, config in enumerate(action_configs)
    ]
    end = node("end")
    all_nodes = [start, *actions, end]
    edges = [edge(all_nodes[i], all_nodes[i + 1]) for i in range(len(all_nodes) - 1)]
    save_graph(version, {"nodes": all_nodes, "edges": edges, "variables": []})
    return actions


@pytest.mark.django_db
class TestUpsert:
    def test_upsert_updates_instead_of_duplicating(self):
        _, version = make_workflow()
        linear_graph(
            version,
            {
                "type": "create_object",
                "model": "applied_control",
                "upsert": True,
                "fields": {"name": "Patch policy", "description": "v1"},
            },
        )
        first = start_instance(version)
        assert first.status == WorkflowInstance.Status.COMPLETED

        # Same graph again: must update the same row.
        version.nodes.filter(type="action").update(
            action_config={
                "type": "create_object",
                "model": "applied_control",
                "upsert": True,
                "fields": {"name": "Patch policy", "description": "v2"},
            }
        )
        second = start_instance(version)
        assert second.status == WorkflowInstance.Status.COMPLETED
        rows = AppliedControl.objects.filter(name="Patch policy")
        assert rows.count() == 1
        assert rows.first().description == "v2"
        log = second.logs.get(event_type="action_executed")
        assert log.data["created"] is False


@pytest.mark.django_db
class TestHttpRequest:
    def test_request_with_secret_header(self, monkeypatch):
        _, version = make_workflow()
        WorkflowSecret.objects.create(
            name="api_token", folder=Folder.get_root_folder(), value="s3cr3t-value"
        )

        captured = {}

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"employee": {"name": "Ada"}}

        def fake_request(method, url, **kwargs):
            captured.update(method=method, url=url, **kwargs)
            return FakeResponse()

        monkeypatch.setattr("requests.request", fake_request)
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda url, **kw: None
        )

        actions = linear_graph(
            version,
            {
                "type": "http_request",
                "method": "GET",
                "url": "https://hris.example.com/employees/42",
                "headers": {"Authorization": "Bearer {{secrets.api_token}}"},
            },
        )
        version.nodes.filter(id=actions[0]["id"]).update(
            output_mapping={"employee_name": "body.employee.name"}
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, list(
            instance.logs.values_list("message", flat=True)
        )
        assert captured["headers"]["Authorization"] == "Bearer s3cr3t-value"
        assert instance.variables["employee_name"] == "Ada"
        # The decrypted secret must not leak into the execution log.
        for log in instance.logs.all():
            assert "s3cr3t-value" not in str(log.data) + log.message

    def test_retry_scheduled_on_network_error(self, monkeypatch):
        import requests

        _, version = make_workflow()

        def failing_request(method, url, **kwargs):
            raise requests.ConnectionError("connection refused")

        monkeypatch.setattr("requests.request", failing_request)
        scheduled = {}
        monkeypatch.setattr(
            "workflows.tasks.retry_token_task.schedule",
            lambda args, delay: scheduled.update(token_id=args[0], delay=delay),
        )

        linear_graph(
            version,
            {
                "type": "http_request",
                "method": "GET",
                "url": "https://api.example.com/x",
            },
            node_extras=[
                {
                    "retry_max_attempts": 3,
                    "retry_delay_seconds": 10,
                    "retry_backoff": "exponential",
                }
            ],
        )
        instance = start_instance(version)
        token = instance.tokens.get(status=WorkflowToken.Status.RETRYING)
        assert token.retry_count == 1
        assert scheduled["delay"] == 10
        assert instance.status == WorkflowInstance.Status.ACTIVE


@pytest.mark.django_db
class TestIamActions:
    def test_provision_folder_with_groups_then_user_and_membership(self):
        _, version = make_workflow()
        provision_folder = {
            "type": "provision_folder",
            "name": "HR — {{payload.department}}",
            "create_default_groups": True,
        }
        provision_user = {
            "type": "provision_user",
            "email": "{{payload.email}}",
            "first_name": "{{payload.first}}",
            "last_name": "{{payload.last}}",
        }
        membership = {
            "type": "manage_group_membership",
            "user": "{{payload.email}}",
            "folder": "{{folder_id}}",
            "builtin_group": "BI-UG-ANA",
            "operation": "add",
        }
        actions = linear_graph(version, provision_folder, provision_user, membership)
        version.nodes.filter(id=actions[0]["id"]).update(
            output_mapping={"folder_id": "folder_id"}
        )
        instance = start_instance(
            version,
            payload={
                "department": "Engineering",
                "email": "ada@example.com",
                "first": "Ada",
                "last": "Lovelace",
            },
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, list(
            instance.logs.values_list("message", flat=True)
        )
        folder = Folder.objects.get(name="HR — Engineering")
        assert folder.content_type == Folder.ContentType.DOMAIN
        groups = UserGroup.objects.filter(folder=folder, builtin=True)
        assert groups.count() >= 5
        user = User.objects.get(email="ada@example.com")
        assert user.first_name == "Ada"
        analysts = UserGroup.objects.get(folder=folder, name="BI-UG-ANA")
        assert analysts in user.user_groups.all()

        # Re-run: everything upserts, no duplicates.
        rerun = start_instance(
            version,
            payload={
                "department": "Engineering",
                "email": "ada@example.com",
                "first": "Ada",
                "last": "Lovelace",
            },
        )
        assert rerun.status == WorkflowInstance.Status.COMPLETED
        assert Folder.objects.filter(name="HR — Engineering").count() == 1
        assert User.objects.filter(email="ada@example.com").count() == 1

    def test_provision_user_deactivation(self):
        _, version = make_workflow()
        User.objects.create_user(email="leaver@example.com")
        linear_graph(
            version,
            {
                "type": "provision_user",
                "email": "leaver@example.com",
                "is_active": "false",
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert User.objects.get(email="leaver@example.com").is_active is False


@pytest.mark.django_db
class TestDeputization:
    def _publish(self, version, user):
        factory = APIRequestFactory()
        view = WorkflowVersionViewSet.as_view({"post": "publish"})
        req = factory.post(f"/api/workflows/workflow-versions/{version.id}/publish/")
        force_authenticate(req, user=user)
        return view(req, pk=str(version.id))

    def test_non_privileged_publisher_is_rejected(self):
        domain = Folder.objects.create(
            name="Deputy domain",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
            create_iam_groups=True,
        )
        Folder.create_default_ug_and_ra(domain)
        manager = User.objects.create_user(email="dma@example.com")
        manager.user_groups.add(UserGroup.objects.get(folder=domain, name="BI-UG-DMA"))

        _, version = make_workflow(folder=domain)
        linear_graph(
            version,
            {"type": "provision_user", "email": "x@example.com"},
        )
        resp = self._publish(version, manager)
        assert resp.status_code == 400
        codes = {e["code"] for e in resp.data["errors"]}
        assert "publisher_permission_missing" in codes

    def test_superuser_publishes(self):
        superuser = User.objects.create_superuser(email="root@example.com")
        _, version = make_workflow()
        linear_graph(
            version,
            {"type": "provision_user", "email": "x@example.com"},
        )
        resp = self._publish(version, superuser)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestWebhookHardening:
    def _hooked_workflow(self):
        workflow, version = make_workflow("Hardened")
        linear_graph(
            version,
            {"type": "log", "message": "ok"},
            trigger={"ref": "hook", "trigger_config": {"type": "webhook"}},
        )
        version.publish()
        return workflow

    def test_hmac_required_when_configured(self):
        import hashlib
        import hmac as hmac_lib
        import json

        workflow = self._hooked_workflow()
        registration = workflow.triggers.get(node_ref="hook")
        registration.hmac_secret = "hmac-key"
        registration.save()
        client = APIClient()
        url = f"/api/workflows/hooks/{workflow.id}/hook/{registration.secret}/"

        resp = client.post(url, {"a": 1}, format="json")
        assert resp.status_code == 403

        body = json.dumps({"a": 1}).encode()
        signature = hmac_lib.new(b"hmac-key", body, hashlib.sha256).hexdigest()
        resp = client.post(
            url,
            body,
            content_type="application/json",
            headers={"X-Hub-Signature-256": f"sha256={signature}"},
        )
        assert resp.status_code == 201, resp.data

    def test_rotate_secret(self):
        from workflows.views import WorkflowTriggerViewSet

        superuser = User.objects.create_superuser(email="rotator@example.com")
        workflow = self._hooked_workflow()
        registration = workflow.triggers.get(node_ref="hook")
        old_secret = registration.secret
        factory = APIRequestFactory()
        view = WorkflowTriggerViewSet.as_view({"post": "rotate_secret"})
        req = factory.post(
            f"/api/workflows/workflow-triggers/{registration.id}/rotate-secret/"
        )
        force_authenticate(req, user=superuser)
        resp = view(req, pk=str(registration.id))
        assert resp.status_code == 200
        registration.refresh_from_db()
        assert registration.secret != old_secret
        assert resp.data["secret"] == registration.secret

        client = APIClient()
        resp = client.post(
            f"/api/workflows/hooks/{workflow.id}/hook/{old_secret}/", {}, format="json"
        )
        assert resp.status_code == 404

    def test_inbound_hooks_kill_switch(self, settings):
        # D23: environments that want no unauthenticated ingress disable all
        # hooks uniformly; a valid URL is indistinguishable from a wrong one.
        workflow = self._hooked_workflow()
        registration = workflow.triggers.get(node_ref="hook")
        url = f"/api/workflows/hooks/{workflow.id}/hook/{registration.secret}/"
        client = APIClient()

        settings.WORKFLOWS_INBOUND_HOOKS = False
        assert client.post(url, {}, format="json").status_code == 404

        settings.WORKFLOWS_INBOUND_HOOKS = True
        assert client.post(url, {}, format="json").status_code == 201


@pytest.mark.django_db
class TestSecretApi:
    def test_value_never_returned(self):
        from workflows.views import WorkflowSecretViewSet

        superuser = User.objects.create_superuser(email="secrets@example.com")
        factory = APIRequestFactory()
        create = WorkflowSecretViewSet.as_view({"post": "create"})
        req = factory.post(
            "/api/workflows/workflow-secrets/",
            {
                "name": "hris_token",
                "folder": str(Folder.get_root_folder().id),
                "value": "super-secret",
            },
            format="json",
        )
        force_authenticate(req, user=superuser)
        resp = create(req)
        assert resp.status_code == 201, resp.data
        assert "super-secret" not in str(resp.data)
        assert "value" not in resp.data

        # Also absent from reads (list/retrieve use the Read serializer).
        retrieve = WorkflowSecretViewSet.as_view({"get": "retrieve"})
        secret = WorkflowSecret.objects.get(name="hris_token")
        read_req = factory.get(f"/api/workflows/workflow-secrets/{secret.id}/")
        force_authenticate(read_req, user=superuser)
        read_resp = retrieve(read_req, pk=str(secret.id))
        assert "super-secret" not in str(read_resp.data)
        assert "value" not in read_resp.data

        assert secret.value == "super-secret"
