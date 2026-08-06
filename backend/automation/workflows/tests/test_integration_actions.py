import uuid

import pytest
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from core.models import AppliedControl
from iam.models import Folder, User, UserGroup
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowSecret,
    WorkflowToken,
    WorkflowVersion,
)
from automation.workflows.views import WorkflowVersionViewSet
from automation.workflows.tests.helpers import publisher_user


def make_workflow(name="Integration flow", folder=None):
    workflow = Workflow.objects.create(
        name=name, folder=folder or Folder.get_root_folder()
    )
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
        workflow, version = make_workflow()
        WorkflowSecret.objects.create(
            workflow=workflow, name="api_token", value="s3cr3t-value"
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

    def test_secrets_are_workflow_scoped(self, monkeypatch):
        """A same-named secret on another workflow must never bleed in: the
        instance resolves only its own workflow's secret."""
        workflow, version = make_workflow()
        WorkflowSecret.objects.create(workflow=workflow, name="api_token", value="mine")
        # Decoy: same name, different workflow, different value.
        other, _ = make_workflow(name="Other flow")
        WorkflowSecret.objects.create(
            workflow=other, name="api_token", value="not-mine"
        )

        captured = {}

        class FakeResponse:
            status_code = 200

            def json(self):
                return {}

        def fake_request(method, url, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

        monkeypatch.setattr("requests.request", fake_request)
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda url, **kw: None
        )

        linear_graph(
            version,
            {
                "type": "http_request",
                "url": "https://api.example.com/x",
                "headers": {"Authorization": "Bearer {{secrets.api_token}}"},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert captured["headers"]["Authorization"] == "Bearer mine"

    def test_retry_scheduled_on_network_error(
        self, monkeypatch, django_capture_on_commit_callbacks
    ):
        import requests

        _, version = make_workflow()

        def failing_request(method, url, **kwargs):
            raise requests.ConnectionError("connection refused")

        monkeypatch.setattr("requests.request", failing_request)
        scheduled = {}
        monkeypatch.setattr(
            "automation.workflows.tasks.retry_token_task.schedule",
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
        # The retry is scheduled on_commit (so the RETRYING row is visible to
        # the consumer); capture-and-execute callbacks to observe it.
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        token = instance.tokens.get(status=WorkflowToken.Status.RETRYING)
        assert token.retry_count == 1
        assert scheduled["delay"] == 10
        assert instance.status == WorkflowInstance.Status.ACTIVE

    def test_redirects_are_not_followed(self, monkeypatch):
        """Only the initial URL is SSRF-checked, so a 3xx must NOT be followed
        to its (unvalidated, possibly internal) Location — it is returned as-is."""
        _, version = make_workflow()
        requested = []

        class Redirect:
            status_code = 302
            headers = {"Location": "http://169.254.169.254/latest/meta-data/"}

            def json(self):
                raise ValueError("no body")

            text = ""

        def fake_request(method, url, **kwargs):
            assert kwargs["allow_redirects"] is False
            requested.append(url)
            return Redirect()

        monkeypatch.setattr("requests.request", fake_request)
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda url, **kw: None
        )

        actions = linear_graph(
            version,
            {"type": "http_request", "url": "https://safe.example.com/redir"},
        )
        version.nodes.filter(id=actions[0]["id"]).update(
            output_mapping={"code": "status"}
        )
        instance = start_instance(version)
        # The 302 comes back unfollowed: exactly one request, to the public URL,
        # and the internal Location is never hit.
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert requested == ["https://safe.example.com/redir"]
        assert instance.variables["code"] == 302

    def test_secret_in_url_not_leaked_on_error(self, monkeypatch):
        workflow, version = make_workflow()
        WorkflowSecret.objects.create(
            workflow=workflow, name="api_key", value="leak-me"
        )

        class ErrorResponse:
            status_code = 500
            is_redirect = False
            next = None

            def json(self):
                return {"error": "boom"}

        monkeypatch.setattr("requests.request", lambda *a, **k: ErrorResponse())
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda url, **kw: None
        )

        linear_graph(
            version,
            {
                "type": "http_request",
                "url": "https://api.example.com/x?token={{secrets.api_key}}",
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert instance.tokens.filter(
            error_message__contains="HTTP 500 from 'api.example.com'"
        ).exists()
        for log in instance.logs.all():
            assert "leak-me" not in str(log.data) + log.message
        for tok in instance.tokens.all():
            assert "leak-me" not in (tok.error_message or "")


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

    def test_membership_cannot_target_ancestor_group(self):
        """A workflow scoped to a child domain must not add a user to a group
        in an ancestor folder (privilege escalation to root global-admin)."""
        domain = Folder.objects.create(
            name="Child domain",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        _, version = make_workflow(folder=domain)
        User.objects.create_user(email="climber@example.com")
        root_admins = UserGroup.objects.get(
            folder=Folder.get_root_folder(), name="BI-UG-ADM"
        )
        linear_graph(
            version,
            {
                "type": "manage_group_membership",
                "user": "climber@example.com",
                "group": str(root_admins.id),
                "operation": "add",
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        user = User.objects.get(email="climber@example.com")
        assert root_admins not in user.user_groups.all()

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

    def test_cannot_remove_last_administrator(self):
        # #4: manage_group_membership must not strip the final global admin
        # (mirrors the core remove-members guard). publisher_user is the sole
        # BI-UG-ADM member in a fresh test DB.
        admin_group = UserGroup.objects.get(
            folder=Folder.get_root_folder(), name="BI-UG-ADM"
        )
        sole_admin = publisher_user()
        assert User.objects.filter(user_groups__name="BI-UG-ADM").count() == 1
        _, version = make_workflow()  # folder = root, run_as = publisher_user
        linear_graph(
            version,
            {
                "type": "manage_group_membership",
                "user": sole_admin.email,
                "group": str(admin_group.id),
                "operation": "remove",
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert sole_admin in admin_group.user_set.all()


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

    def test_domain_scoped_user_perms_cannot_publish_provisioning(self):
        # #4: provision_user is authorized at the ROOT folder, so a publisher
        # holding add_user/change_user only in a domain fails deputization even
        # though it can otherwise manage the workflow there.
        from django.contrib.auth.models import Permission
        from iam.models import Role, RoleAssignment

        domain = Folder.objects.create(
            name="DomainDeputy",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        publisher = User.objects.create_user(email="domdeputy@example.com")
        role = Role.objects.create(name="domain-user-role")
        role.permissions.set(
            Permission.objects.filter(
                codename__in=[
                    "change_workflowversion",
                    "view_workflowversion",
                    "view_folder",
                    "add_user",
                    "change_user",
                ]
            )
        )
        ra = RoleAssignment.objects.create(
            user=publisher, role=role, folder=domain, is_recursive=True
        )
        ra.perimeter_folders.add(domain)

        _, version = make_workflow(folder=domain)
        linear_graph(version, {"type": "provision_user", "email": "x@example.com"})
        resp = self._publish(version, publisher)
        assert resp.status_code == 400
        codes = {e["code"] for e in resp.data["errors"]}
        assert "publisher_permission_missing" in codes


@pytest.mark.django_db
class TestWebhookHardening:
    def _hooked_workflow(self):
        workflow, version = make_workflow("Hardened")
        linear_graph(
            version,
            {"type": "log", "message": "ok"},
            trigger={"ref": "hook", "trigger_config": {"type": "webhook"}},
        )
        version.publish(publisher_user())
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
        from automation.workflows.views import WorkflowTriggerViewSet

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
        # Environments that want no unauthenticated ingress disable all
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
        from automation.workflows.views import WorkflowSecretViewSet

        superuser = User.objects.create_superuser(email="secrets@example.com")
        workflow, _ = make_workflow()
        factory = APIRequestFactory()
        create = WorkflowSecretViewSet.as_view({"post": "create"})
        req = factory.post(
            "/api/workflows/workflow-secrets/",
            {
                "name": "hris_token",
                "workflow": str(workflow.id),
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
