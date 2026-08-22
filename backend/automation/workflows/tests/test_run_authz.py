"""Workflow run authorization: definer rights checked live.

The version wields its publisher's authority (run_as), whoever triggers it;
drafts run as the invoker. Enforcement is per action node at runtime, refusal
is a retryable node failure, and reads are intersected with the identity's
view scope. No superuser bypass — every identity flows through the same
kernel verdict.
"""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from core.models import AppliedControl
from iam.models import Folder, Role, RoleAssignment, User, UserGroup
from automation.workflows.engine import run_identity, start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowInstanceLog,
    WorkflowTrigger,
    WorkflowVersion,
)
from automation.workflows.tests.helpers import publisher_user
from automation.workflows.views import WorkflowInstanceViewSet


def node(type_, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(a, b, **kwargs):
    return {"id": str(uuid.uuid4()), "source": a["id"], "target": b["id"], **kwargs}


def make_domain(name):
    return Folder.objects.create(
        name=name,
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def grant(user, folder, codenames, recursive=True):
    """Give a user a bespoke role holding `codenames` on `folder`. view_folder
    is always included: the kernel's object-scoping (get_accessible_object_ids)
    skips any assignment whose role can't see folders — every real role holds
    it, so a test role without it would be unrealistic."""
    role = Role.objects.create(name=f"role-{uuid.uuid4()}")
    role.permissions.set(
        Permission.objects.filter(codename__in=[*codenames, "view_folder"])
    )
    ra = RoleAssignment.objects.create(
        user=user, role=role, folder=folder, is_recursive=recursive
    )
    ra.perimeter_folders.add(folder)
    return ra


def publish_as(version, identity):
    """Publish (stamps the publisher, passing deputization as a superuser)
    then override run_as to the identity under test."""
    version.publish(publisher_user())
    version.run_as = identity
    version.save(update_fields=["run_as"])


def create_control_workflow(name, folder):
    """trigger -> create AppliedControl -> end, published, run_as = publisher."""
    workflow = Workflow.objects.create(name=name, folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow)
    trigger = node("trigger", trigger_config={"type": "manual"})
    act = node(
        "action",
        label="Make control",
        action_config={
            "type": "create_object",
            "model": "applied_control",
            "fields": {"name": "From workflow"},
        },
    )
    end = node("end")
    save_graph(
        version,
        {
            "nodes": [trigger, act, end],
            "edges": [edge(trigger, act), edge(act, end)],
            "variables": [],
        },
    )
    return workflow, version


@pytest.mark.django_db
class TestPublishStampsIdentity:
    def test_publish_stamps_both_fields(self):
        user = publisher_user()
        _, version = create_control_workflow("Stamp", Folder.get_root_folder())
        version.publish(user)
        version.refresh_from_db()
        assert version.published_by_id == user.id
        assert version.run_as_id == user.id


@pytest.mark.django_db
class TestRuntimeEnforcement:
    def test_denied_run_fails_then_resumes_after_grant(self):
        # run_as holds add_workflowinstance (to be startable) but NOT
        # add_appliedcontrol → the create action is denied.
        domain = make_domain("Enforce")
        runner = User.objects.create_user(email="runner@authz.test")
        grant(runner, domain, ["add_workflowinstance"])
        workflow, version = create_control_workflow("Enforce", domain)
        publish_as(version, runner)

        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert instance.logs.filter(
            event_type=WorkflowInstanceLog.EventType.AUTHORIZATION_DENIED
        ).exists()
        assert not AppliedControl.objects.filter(name="From workflow").exists()

        # Grant the missing permission, retry the errored token → completes.
        grant(runner, domain, ["add_workflowinstance", "add_appliedcontrol"])
        from automation.workflows.engine import retry_token
        from automation.workflows.models import WorkflowToken

        token = instance.tokens.get(status=WorkflowToken.Status.ERROR)
        retry_token(token)
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert AppliedControl.objects.filter(name="From workflow").exists()

    def test_authorized_identity_runs(self):
        domain = make_domain("Allowed")
        runner = User.objects.create_user(email="ok@authz.test")
        grant(runner, domain, ["add_workflowinstance", "add_appliedcontrol"])
        _, version = create_control_workflow("Allowed", domain)
        publish_as(version, runner)
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED

    def test_revocation_stops_future_runs(self):
        domain = make_domain("Revoke")
        runner = User.objects.create_user(email="revoke@authz.test")
        ra = grant(runner, domain, ["add_workflowinstance", "add_appliedcontrol"])
        _, version = create_control_workflow("Revoke", domain)
        publish_as(version, runner)
        assert start_instance(version).status == WorkflowInstance.Status.COMPLETED
        ra.delete()  # offboard
        assert start_instance(version).status == WorkflowInstance.Status.FAILED

    def test_inactive_identity_refused(self):
        domain = make_domain("Inactive")
        runner = User.objects.create_user(email="inactive@authz.test")
        grant(runner, domain, ["add_workflowinstance", "add_appliedcontrol"])
        _, version = create_control_workflow("Inactive", domain)
        publish_as(version, runner)
        runner.is_active = False
        runner.save(update_fields=["is_active"])
        assert start_instance(version).status == WorkflowInstance.Status.FAILED


@pytest.mark.django_db
class TestNullIdentityGuards:
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

    def test_manual_run_rejects_null_identity(self):
        admin = publisher_user()
        _, version = create_control_workflow("NullRun", Folder.get_root_folder())
        version.publish(admin)
        WorkflowVersion.objects.filter(id=version.id).update(run_as=None)
        resp = self._post(str(version.id), admin)
        assert resp.status_code == 400
        assert resp.data["error"] == "republishRequired"


@pytest.mark.django_db
class TestDraftRunsAsInvoker:
    def test_draft_uses_invoker_identity(self):
        # A draft has no run_as; the run acts as whoever starts it.
        domain = make_domain("Draft")
        runner = User.objects.create_user(email="draft@authz.test")
        grant(runner, domain, ["add_appliedcontrol"])
        _, version = create_control_workflow("Draft", domain)  # stays draft
        assert version.is_draft and version.run_as is None
        instance = start_instance(version, initiated_by=runner)
        assert run_identity(instance) == runner
        assert instance.status == WorkflowInstance.Status.COMPLETED

    def test_draft_denies_unprivileged_invoker(self):
        domain = make_domain("DraftDeny")
        runner = User.objects.create_user(email="draftdeny@authz.test")
        # no add_appliedcontrol
        _, version = create_control_workflow("DraftDeny", domain)
        instance = start_instance(version, initiated_by=runner)
        assert instance.status == WorkflowInstance.Status.FAILED


@pytest.mark.django_db
class TestReadIntersection:
    def test_row_outside_identity_scope_is_invisible(self):
        # Workflow in a parent domain, run_as scoped to it; a control lives in
        # a child enclave the identity cannot view → excluded even though the
        # child is inside the workflow's subtree scope.
        parent = make_domain("ReadParent")
        child = Folder.objects.create(
            name="Enclave",
            parent_folder=parent,
            content_type=Folder.ContentType.DOMAIN,
        )
        AppliedControl.objects.create(name="Hidden", folder=child)
        AppliedControl.objects.create(name="Visible", folder=parent)

        runner = User.objects.create_user(email="reader@authz.test")
        # non-recursive: sees parent rows, NOT the child enclave
        grant(runner, parent, ["view_appliedcontrol"], recursive=False)

        workflow = Workflow.objects.create(name="Reader", folder=parent)
        version = WorkflowVersion.objects.create(workflow=workflow)
        trigger = node("trigger", trigger_config={"type": "manual"})
        read = node(
            "action",
            label="Read",
            action_config={
                "type": "read_objects",
                "model": "applied_control",
                "mode": "list",
            },
            output_mapping={"controls": "results"},
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [trigger, read, end],
                "edges": [edge(trigger, read), edge(read, end)],
                "variables": [],
            },
        )
        publish_as(version, runner)

        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        names = {c["name"] for c in instance.variables.get("controls", [])}
        assert "Visible" in names
        assert "Hidden" not in names


@pytest.mark.django_db
class TestNoSuperuserBypass:
    def test_superuser_identity_flows_through_kernel(self):
        # A superuser is in BI-UG-ADM, so it passes the SAME can() path — the
        # point is that no wrapper short-circuits is_superuser. Assert the
        # can() verdict comes from the kernel, not a bypass.
        from automation.workflows import authz

        admin = publisher_user()  # superuser (BI-UG-ADM)
        root = Folder.get_root_folder()
        assert authz.can(admin, "add_appliedcontrol", root) is True

        # A superuser flag with NO role assignment must NOT pass — proving the
        # verdict is the kernel's, not an is_superuser fast path.
        rogue = User.objects.create(email="rogue@authz.test", is_superuser=True)
        rogue.user_groups.clear()
        assert authz.can(rogue, "add_appliedcontrol", root) is False


@pytest.mark.django_db
class TestSubprocessIdentity:
    def test_subprocess_child_needs_identity(self):
        from automation.workflows.engine import EngineError, _start_subprocess
        from automation.workflows.models import WorkflowToken

        child_wf = Workflow.objects.create(
            name="Child", folder=Folder.get_root_folder()
        )
        child_v = WorkflowVersion.objects.create(workflow=child_wf)
        save_graph(
            child_v,
            {
                "nodes": [
                    node("trigger", trigger_config={"type": "manual"}),
                    node("end"),
                ],
                "edges": [],
                "variables": [],
            },
        )
        # publish without setting run_as, then null it to simulate legacy
        child_v.publish(publisher_user())
        WorkflowVersion.objects.filter(id=child_v.id).update(run_as=None)

        parent_wf = Workflow.objects.create(
            name="Parent", folder=Folder.get_root_folder()
        )
        parent_v = WorkflowVersion.objects.create(
            workflow=parent_wf, run_as=publisher_user()
        )
        sub = node("subprocess")
        save_graph(
            parent_v,
            {
                "nodes": [
                    node("trigger", trigger_config={"type": "manual"}),
                    sub,
                    node("end"),
                ],
                "edges": [],
                "variables": [],
            },
        )
        instance = WorkflowInstance.objects.create(
            workflow=parent_wf, version=parent_v, folder=parent_wf.folder
        )
        sub_node = parent_v.nodes.get(type="subprocess")
        sub_node.subprocess_workflow = child_wf
        sub_node.save(update_fields=["subprocess_workflow"])
        token = WorkflowToken.objects.create(instance=instance, current_node=sub_node)
        with pytest.raises(EngineError, match="run identity"):
            _start_subprocess(token)

    def test_subprocess_out_of_scope_rejected(self):
        """A subprocess pointing at a workflow in an unrelated domain is refused
        at run time (fail closed), so it can never run as that workflow's
        run_as or leak its outputs back into the caller's run."""
        from automation.workflows.engine import EngineError, _start_subprocess
        from automation.workflows.models import WorkflowToken

        domain_a = make_domain("Alpha")
        domain_b = make_domain("Bravo")

        # Child lives in a sibling domain, published with a valid run identity.
        child_wf = Workflow.objects.create(name="Foreign child", folder=domain_b)
        child_v = WorkflowVersion.objects.create(workflow=child_wf)
        save_graph(
            child_v,
            {
                "nodes": [
                    node("trigger", trigger_config={"type": "manual"}),
                    node("end"),
                ],
                "edges": [],
                "variables": [],
            },
        )
        child_v.publish(publisher_user())

        parent_wf = Workflow.objects.create(name="Parent", folder=domain_a)
        parent_v = WorkflowVersion.objects.create(
            workflow=parent_wf, run_as=publisher_user()
        )
        save_graph(
            parent_v,
            {
                "nodes": [
                    node("trigger", trigger_config={"type": "manual"}),
                    node("subprocess"),
                    node("end"),
                ],
                "edges": [],
                "variables": [],
            },
        )
        instance = WorkflowInstance.objects.create(
            workflow=parent_wf, version=parent_v, folder=parent_wf.folder
        )
        sub_node = parent_v.nodes.get(type="subprocess")
        sub_node.subprocess_workflow = child_wf
        sub_node.save(update_fields=["subprocess_workflow"])
        token = WorkflowToken.objects.create(instance=instance, current_node=sub_node)
        with pytest.raises(EngineError, match="outside this workflow's scope"):
            _start_subprocess(token)


@pytest.mark.django_db
class TestApiParity:
    """The engine must see exactly what the API shows the identity — this is
    the load-bearing claim behind using get_accessible_object_ids, and the
    tripwire for PR #4364's kernel rewrite."""

    def test_engine_read_matches_api_visibility(self):
        from core.views import AppliedControlViewSet
        from automation.workflows import authz

        parent = make_domain("Parity")
        child = Folder.objects.create(
            name="Enclave",
            parent_folder=parent,
            content_type=Folder.ContentType.DOMAIN,
        )
        AppliedControl.objects.create(name="ParentCtl", folder=parent)
        AppliedControl.objects.create(name="ChildCtl", folder=child)
        runner = User.objects.create_user(email="parity@authz.test")
        grant(runner, parent, ["view_appliedcontrol"], recursive=False)

        engine_ids = set(authz.viewable_ids(runner, AppliedControl))

        factory = APIRequestFactory()
        view = AppliedControlViewSet.as_view({"get": "list"})
        req = factory.get("/api/applied-controls/")
        force_authenticate(req, user=runner)
        api_ids = {uuid.UUID(row["id"]) for row in view(req).data["results"]}

        assert engine_ids == api_ids

    def test_create_parity(self):
        # For a fixed identity: engine create allowed iff the API would allow
        # the same create. Assert both directions with one privileged and one
        # unprivileged identity.
        from core.views import AppliedControlViewSet

        domain = make_domain("CreateParity")

        def api_create(identity):
            factory = APIRequestFactory()
            view = AppliedControlViewSet.as_view({"post": "create"})
            req = factory.post(
                "/api/applied-controls/",
                {"name": f"api-{uuid.uuid4()}", "folder": str(domain.id)},
                format="json",
            )
            force_authenticate(req, user=identity)
            return view(req).status_code

        def engine_create_ok(identity):
            _, version = create_control_workflow(f"cp-{uuid.uuid4()}", domain)
            publish_as(version, identity)
            return start_instance(version).status == WorkflowInstance.Status.COMPLETED

        privileged = User.objects.create_user(email="cp-yes@authz.test")
        grant(privileged, domain, ["add_appliedcontrol"])
        assert engine_create_ok(privileged) is True
        assert api_create(privileged) == 201

        unprivileged = User.objects.create_user(email="cp-no@authz.test")
        grant(unprivileged, domain, ["view_appliedcontrol"])  # can see, not add
        assert engine_create_ok(unprivileged) is False
        assert api_create(unprivileged) == 403


# --- automation entry-point builders (registrations require publish) ---


def build_webhook_workflow(name, folder, identity):
    workflow = Workflow.objects.create(name=name, folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow)
    trigger = node("trigger", ref="hook", trigger_config={"type": "webhook"})
    act = node(
        "action",
        action_config={
            "type": "create_object",
            "model": "applied_control",
            "fields": {"name": "hook control"},
        },
    )
    END = node("end")
    save_graph(
        version,
        {
            "nodes": [trigger, act, END],
            "edges": [edge(trigger, act), edge(act, END)],
            "variables": [],
        },
    )
    publish_as(version, identity)
    return workflow, version


def build_schedule_workflow(name, folder, identity):
    workflow = Workflow.objects.create(name=name, folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow)
    trigger = node(
        "trigger",
        ref="nightly",
        trigger_config={"type": "schedule", "cron_expression": "*/10 * * * *"},
    )
    act = node("action", action_config={"type": "log", "message": "tick"})
    END = node("end")
    save_graph(
        version,
        {
            "nodes": [trigger, act, END],
            "edges": [edge(trigger, act), edge(act, END)],
            "variables": [],
        },
    )
    publish_as(version, identity)
    workflow.triggers.filter(node_ref="nightly").update(enabled=True)
    return workflow, version


def build_event_workflow(name, folder, identity, event_key="appliedcontrol.updated"):
    workflow = Workflow.objects.create(name=name, folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow)
    trigger = node(
        "trigger",
        ref="on_event",
        trigger_config={"type": "internal_event", "event_key": event_key},
    )
    act = node("action", action_config={"type": "log", "message": "fired"})
    END = node("end")
    save_graph(
        version,
        {
            "nodes": [trigger, act, END],
            "edges": [edge(trigger, act), edge(act, END)],
            "variables": [],
        },
    )
    publish_as(version, identity)
    workflow.triggers.filter(node_ref="on_event").update(enabled=True)
    return workflow, version


@pytest.fixture
def no_run(monkeypatch):
    """Intercept async run dispatch so entry-point tests observe which
    instances were created without executing them."""
    calls = []
    monkeypatch.setattr("automation.workflows.tasks.run_instance_task", calls.append)
    return calls


@pytest.mark.django_db
class TestAutomationEntryPoints:
    """Webhook / scheduler / events all refuse to fire a version without a
    run identity — the automation paths have no human to notice a failure."""

    def test_webhook_null_identity_returns_404(self):
        from rest_framework.test import APIClient

        admin = publisher_user()
        workflow, version = build_webhook_workflow(
            "HookNoId", Folder.get_root_folder(), admin
        )
        secret = workflow.triggers.get(node_ref="hook").secret
        # A valid secret still 404s once the identity is gone (no oracle).
        WorkflowVersion.objects.filter(id=version.id).update(run_as=None)
        resp = APIClient().post(
            f"/api/workflows/hooks/{workflow.id}/hook/{secret}/", {}, format="json"
        )
        assert resp.status_code == 404

    def test_scheduler_skips_null_identity_and_advances(self, no_run):
        from automation.workflows.scheduling import run_due_schedules

        admin = publisher_user()
        workflow, version = build_schedule_workflow(
            "SchedNoId", Folder.get_root_folder(), admin
        )
        reg = workflow.triggers.get(node_ref="nightly")
        WorkflowTrigger.objects.filter(id=reg.id).update(
            next_run_at=timezone.now() - timedelta(minutes=1)
        )
        WorkflowVersion.objects.filter(id=version.id).update(run_as=None)
        before = WorkflowTrigger.objects.get(id=reg.id).next_run_at

        assert run_due_schedules() == []
        reg.refresh_from_db()
        assert reg.last_result == WorkflowTrigger.Result.SKIPPED_NO_IDENTITY
        # CAS already advanced next_run_at — republishing resumes on the next
        # occurrence, no catch-up storm.
        assert reg.next_run_at > before
        assert no_run == []

    def test_events_skip_null_identity_but_fire_siblings(self, no_run):
        from automation.workflows.events import dispatch_internal_event

        admin = publisher_user()
        root = Folder.get_root_folder()
        _, no_id = build_event_workflow("EvtNoId", root, admin)
        live_wf, _ = build_event_workflow("EvtLive", root, admin)
        WorkflowVersion.objects.filter(id=no_id.id).update(run_as=None)

        started = dispatch_internal_event(
            "appliedcontrol.updated",
            {
                "event_key": "appliedcontrol.updated",
                "model": "appliedcontrol",
                "operation": "updated",
                "object_id": str(uuid.uuid4()),
                "object_repr": "x",
                "changes": {},
                "new_values": {},
                "folder_id": None,
                "actor_email": None,
                "timestamp": None,
            },
            None,
        )
        # Only the identity-bearing sibling fired; the null-identity one was
        # skipped per-trigger, not the whole dispatch.
        assert len(started) == 1
        assert started[0].workflow_id == live_wf.id
        no_id.workflow.triggers.get(node_ref="on_event").refresh_from_db()
        assert (
            no_id.workflow.triggers.get(node_ref="on_event").last_result
            == WorkflowTrigger.Result.SKIPPED_NO_IDENTITY
        )


@pytest.mark.django_db
class TestPrivilegeBranches:
    """Every codename required_permissions can emit must be enforced, not just
    create_object's add_."""

    def _run_action(self, action_config, domain, identity):
        workflow = Workflow.objects.create(name=f"pb-{uuid.uuid4()}", folder=domain)
        version = WorkflowVersion.objects.create(workflow=workflow)
        trigger = node("trigger", trigger_config={"type": "manual"})
        act = node("action", action_config=action_config)
        END = node("end")
        save_graph(
            version,
            {
                "nodes": [trigger, act, END],
                "edges": [edge(trigger, act), edge(act, END)],
                "variables": [],
            },
        )
        publish_as(version, identity)
        return start_instance(version)

    def test_upsert_needs_change_permission(self):
        # add_ alone lets create; upsert also needs change_.
        domain = make_domain("Upsert")
        runner = User.objects.create_user(email="upsert@authz.test")
        grant(runner, domain, ["add_appliedcontrol"])  # not change_
        instance = self._run_action(
            {
                "type": "create_object",
                "model": "applied_control",
                "fields": {"name": "up"},
                "upsert": True,
            },
            domain,
            runner,
        )
        assert instance.status == WorkflowInstance.Status.FAILED
        assert instance.logs.filter(
            event_type=WorkflowInstanceLog.EventType.AUTHORIZATION_DENIED
        ).exists()

        grant(runner, domain, ["add_appliedcontrol", "change_appliedcontrol"])
        instance2 = self._run_action(
            {
                "type": "create_object",
                "model": "applied_control",
                "fields": {"name": "up2"},
                "upsert": True,
            },
            domain,
            runner,
        )
        assert instance2.status == WorkflowInstance.Status.COMPLETED

    def test_provision_folder_denied_without_change_folder(self):
        domain = make_domain("ProvFolder")
        runner = User.objects.create_user(email="pf@authz.test")
        grant(runner, domain, ["add_folder"])  # missing change_folder
        instance = self._run_action(
            {"type": "provision_folder", "name": "sub"}, domain, runner
        )
        assert instance.status == WorkflowInstance.Status.FAILED

    def test_provision_user_denied_without_perms(self):
        domain = make_domain("ProvUser")
        runner = User.objects.create_user(email="pu@authz.test")
        grant(runner, domain, ["add_user"])  # missing change_user
        instance = self._run_action(
            {"type": "provision_user", "email": "new@x.test"}, domain, runner
        )
        assert instance.status == WorkflowInstance.Status.FAILED

    def test_manage_group_membership_denied_without_perms(self):
        domain = make_domain("MgmDenied")
        runner = User.objects.create_user(email="mgm@authz.test")
        grant(runner, domain, ["change_user"])  # missing change_usergroup
        instance = self._run_action(
            {
                "type": "manage_group_membership",
                "user": "mgm@authz.test",
                "group": str(uuid.uuid4()),
            },
            domain,
            runner,
        )
        assert instance.status == WorkflowInstance.Status.FAILED

    def test_manage_group_membership_out_of_scope_group_rejected(self):
        # G7: even with both perms, the target group must be inside the
        # workflow's subtree — no adding users to root's BI-UG-ADM.
        domain = Folder.objects.create(
            name=f"ScopeDom-{uuid.uuid4()}",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
            create_iam_groups=True,
        )
        Folder.create_default_ug_and_ra(domain)
        runner = User.objects.create_user(email="mgmscope@authz.test")
        grant(runner, domain, ["change_user", "change_usergroup"])
        root_group = UserGroup.objects.filter(
            folder=Folder.get_root_folder(), builtin=True
        ).first()
        assert root_group is not None
        instance = self._run_action(
            {
                "type": "manage_group_membership",
                "user": "mgmscope@authz.test",
                "group": str(root_group.id),
            },
            domain,
            runner,
        )
        # ActionError "outside this workflow's scope" → run fails.
        assert instance.status == WorkflowInstance.Status.FAILED

    def test_provision_user_denied_with_domain_scoped_perms(self):
        # #4: user provisioning is a GLOBAL operation — a domain-scoped
        # add_user/change_user must not authorize it, since the user API itself
        # gates user creation at the root folder.
        domain = make_domain("DomainUserOnly")
        runner = User.objects.create_user(email="domonly@authz.test")
        grant(runner, domain, ["add_user", "change_user"])  # at domain, not root
        instance = self._run_action(
            {"type": "provision_user", "email": "victim@x.test"}, domain, runner
        )
        assert instance.status == WorkflowInstance.Status.FAILED
        assert instance.logs.filter(
            event_type=WorkflowInstanceLog.EventType.AUTHORIZATION_DENIED
        ).exists()
        assert not User.objects.filter(email="victim@x.test").exists()

    def test_provision_user_allowed_with_root_scoped_perms(self):
        # The same grant at the ROOT folder authorizes it, matching the API.
        runner = User.objects.create_user(email="rootonly@authz.test")
        grant(runner, Folder.get_root_folder(), ["add_user", "change_user"])
        domain = make_domain("RootUserOk")
        instance = self._run_action(
            {"type": "provision_user", "email": "hire@x.test"}, domain, runner
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, list(
            instance.logs.values_list("message", flat=True)
        )
        assert User.objects.filter(email="hire@x.test").exists()

    def test_membership_authorized_by_change_usergroup_alone(self):
        # #4: membership is a group mutation — change_usergroup on the group's
        # folder suffices (no root-scoped change_user), matching core
        # add-members / remove-members.
        domain = Folder.objects.create(
            name=f"MembOk-{uuid.uuid4()}",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
            create_iam_groups=True,
        )
        Folder.create_default_ug_and_ra(domain)
        member = User.objects.create_user(email="member@authz.test")
        runner = User.objects.create_user(email="mgr@authz.test")
        grant(runner, domain, ["change_usergroup"])  # NOT change_user
        analysts = UserGroup.objects.get(folder=domain, name="BI-UG-ANA")
        instance = self._run_action(
            {
                "type": "manage_group_membership",
                "user": "member@authz.test",
                "group": str(analysts.id),
                "operation": "add",
            },
            domain,
            runner,
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, list(
            instance.logs.values_list("message", flat=True)
        )
        assert analysts in member.user_groups.all()


@pytest.mark.django_db
class TestApiInterplay:
    """The invoker's right to START and the definer's authority to ACT are
    separate layers."""

    def test_invoker_starts_but_run_as_denied_fails_run(self):
        domain = make_domain("Interplay")
        invoker = User.objects.create_user(email="invoker@authz.test")
        # view_workflowversion so the version resolves (the create endpoint
        # scopes the lookup to viewable versions), add_workflowinstance to
        # start. A real runner navigating to the workflow holds both.
        grant(invoker, domain, ["add_workflowinstance", "view_workflowversion"])
        run_as = User.objects.create_user(email="weakrunas@authz.test")
        grant(run_as, domain, ["view_appliedcontrol"])  # may NOT add
        _, version = create_control_workflow("Interplay", domain)
        publish_as(version, run_as)

        factory = APIRequestFactory()
        view = WorkflowInstanceViewSet.as_view({"post": "create"})
        req = factory.post(
            "/api/workflows/workflow-instances/",
            {"version": str(version.id)},
            format="json",
        )
        force_authenticate(req, user=invoker)
        resp = view(req)
        # The run STARTS (invoker allowed) but ends FAILED (run_as denied).
        assert resp.status_code == 201, resp.data
        assert resp.data["status"] == "failed"


@pytest.mark.django_db
class TestRepublishStamping:
    def test_republish_by_different_user_diverges(self):
        alice = User.objects.create_superuser(email="alice@authz.test")
        bob = User.objects.create_superuser(email="bob@authz.test")
        workflow, v1 = create_control_workflow("Multi", Folder.get_root_folder())
        v1.publish(alice)
        v1.refresh_from_db()
        assert v1.run_as_id == alice.id

        draft = v1.clone_as_draft()
        draft.publish(bob)
        draft.refresh_from_db()
        v1.refresh_from_db()
        assert draft.run_as_id == bob.id
        assert draft.status == WorkflowVersion.Status.PUBLISHED
        # Archived v1 keeps alice — provenance is per-version.
        assert v1.run_as_id == alice.id
        assert v1.status == WorkflowVersion.Status.ARCHIVED


@pytest.mark.django_db
class TestDeputizationReport:
    def test_collect_required_permissions_lists_action_codenames(self):
        from automation.workflows.views import collect_required_permissions

        _, version = create_control_workflow("Report", Folder.get_root_folder())
        report = collect_required_permissions(version)
        codenames = {c for entry in report for c in entry["codenames"]}
        assert "add_appliedcontrol" in codenames
        assert all({"node_id", "label", "codenames"} <= set(e) for e in report)

    def test_required_permissions_endpoint(self):
        from automation.workflows.views import WorkflowVersionViewSet

        _, version = create_control_workflow("ReportEp", Folder.get_root_folder())
        factory = APIRequestFactory()
        view = WorkflowVersionViewSet.as_view({"get": "required_permissions"})
        req = factory.get(
            f"/api/workflows/workflow-versions/{version.id}/required-permissions/"
        )
        force_authenticate(req, user=publisher_user())
        resp = view(req, pk=str(version.id))
        assert resp.status_code == 200
        codenames = {c for entry in resp.data for c in entry["codenames"]}
        assert "add_appliedcontrol" in codenames


@pytest.mark.django_db
class TestIdentitySerialization:
    def test_version_read_exposes_identity(self):
        from automation.workflows.serializers import WorkflowVersionReadSerializer

        admin = publisher_user()
        _, version = create_control_workflow("Ser", Folder.get_root_folder())
        version.publish(admin)
        version.refresh_from_db()
        data = WorkflowVersionReadSerializer(version).data
        assert data["run_as"]["email"] == admin.email
        assert data["published_by"]["email"] == admin.email

    def test_instance_run_as_shows_invoker_for_draft(self):
        from automation.workflows.serializers import WorkflowInstanceReadSerializer

        domain = make_domain("SerInst")
        runner = User.objects.create_user(email="serinst@authz.test")
        grant(runner, domain, ["add_appliedcontrol"])
        _, version = create_control_workflow("SerInst", domain)  # draft
        instance = start_instance(version, initiated_by=runner)
        data = WorkflowInstanceReadSerializer(instance).data
        assert data["run_as"] == runner.email


@pytest.mark.django_db
class TestIdentityEdgeCases:
    def test_no_permission_action_runs_without_identity(self):
        # A log-only draft with no invoker: run_identity is None but the
        # action needs no permission, so it must still run.
        _, version = _log_only_workflow()
        instance = start_instance(version)  # initiated_by=None
        assert run_identity(instance) is None
        assert instance.status == WorkflowInstance.Status.COMPLETED

    def test_draft_with_inactive_invoker_refused(self):
        domain = make_domain("InactiveInvoker")
        runner = User.objects.create_user(email="inactinv@authz.test")
        grant(runner, domain, ["add_appliedcontrol"])
        runner.is_active = False
        runner.save(update_fields=["is_active"])
        _, version = create_control_workflow("InactiveInvoker", domain)  # draft
        instance = start_instance(version, initiated_by=runner)
        assert instance.status == WorkflowInstance.Status.FAILED

    def test_created_object_lands_in_instance_folder(self):
        # Folder-lock regression (actions.py:278): the payload cannot steer
        # where a created object lands.
        domain = make_domain("FolderLock")
        runner = User.objects.create_user(email="folderlock@authz.test")
        grant(runner, domain, ["add_appliedcontrol"])
        _, version = create_control_workflow("FolderLock", domain)
        publish_as(version, runner)
        assert start_instance(version).status == WorkflowInstance.Status.COMPLETED
        ctl = AppliedControl.objects.get(name="From workflow", folder=domain)
        assert ctl.folder_id == domain.id

    def test_loop_body_action_denial_fails_run(self):
        # authorize_action fires per loop iteration.
        domain = make_domain("LoopDeny")
        runner = User.objects.create_user(email="loopdeny@authz.test")
        grant(runner, domain, ["add_workflowinstance"])  # no add_appliedcontrol
        version = _loop_create_workflow(domain)
        publish_as(version, runner)
        instance = start_instance(version, payload={"items": ["a", "b"]})
        assert instance.status == WorkflowInstance.Status.FAILED
        assert instance.logs.filter(
            event_type=WorkflowInstanceLog.EventType.AUTHORIZATION_DENIED
        ).exists()


def _log_only_workflow():
    workflow = Workflow.objects.create(
        name=f"log-{uuid.uuid4()}", folder=Folder.get_root_folder()
    )
    version = WorkflowVersion.objects.create(workflow=workflow)
    trigger = node("trigger", trigger_config={"type": "manual"})
    act = node("action", action_config={"type": "log", "message": "hi"})
    END = node("end")
    save_graph(
        version,
        {
            "nodes": [trigger, act, END],
            "edges": [edge(trigger, act), edge(act, END)],
            "variables": [],
        },
    )
    return workflow, version


def _loop_create_workflow(domain):
    workflow = Workflow.objects.create(name=f"loop-{uuid.uuid4()}", folder=domain)
    version = WorkflowVersion.objects.create(workflow=workflow)
    trigger = node(
        "trigger",
        trigger_config={"type": "manual"},
        input_mapping={"items": "items"},
    )
    loop = node(
        "loop",
        label="Per item",
        loop_config={"collection": "{{items}}", "on_item_error": "stop"},
    )
    body = node(
        "action",
        action_config={
            "type": "create_object",
            "model": "applied_control",
            "fields": {"name": "loop {{item}}"},
        },
    )
    end = node("end")
    save_graph(
        version,
        {
            "nodes": [trigger, loop, body, end],
            "edges": [
                edge(trigger, loop),
                edge(loop, body, source_port="each"),
                edge(body, loop),
                edge(loop, end, source_port="done"),
            ],
            "variables": [
                {"id": str(uuid.uuid4()), "key": "items", "type": "json"},
            ],
        },
    )
    return version


@pytest.mark.django_db
class TestOwnershipImmutability:
    """#5: ownership FKs are frozen after create, so a caller can't reparent a
    row into a scope they don't control (e.g. poison another workflow's
    secrets)."""

    def test_secret_workflow_fk_is_immutable(self):
        from rest_framework.exceptions import PermissionDenied

        from automation.workflows.models import WorkflowSecret
        from automation.workflows.serializers import WorkflowSecretWriteSerializer

        root = Folder.get_root_folder()
        wf_a = Workflow.objects.create(name="secret-a", folder=root)
        wf_b = Workflow.objects.create(name="secret-b", folder=root)
        secret = WorkflowSecret.objects.create(workflow=wf_a, name="TOKEN", value="v")

        serializer = WorkflowSecretWriteSerializer(instance=secret)
        # Keeping the same workflow is fine; moving to another is refused.
        assert serializer.validate_workflow(wf_a) == wf_a
        with pytest.raises(PermissionDenied):
            serializer.validate_workflow(wf_b)

    def test_version_workflow_fk_is_immutable(self):
        from rest_framework.exceptions import PermissionDenied

        from automation.workflows.serializers import WorkflowVersionWriteSerializer

        root = Folder.get_root_folder()
        wf_a = Workflow.objects.create(name="ver-a", folder=root)
        wf_b = Workflow.objects.create(name="ver-b", folder=root)
        version = WorkflowVersion.objects.create(workflow=wf_a)

        serializer = WorkflowVersionWriteSerializer(instance=version)
        assert serializer.validate_workflow(wf_a) == wf_a
        with pytest.raises(PermissionDenied):
            serializer.validate_workflow(wf_b)


@pytest.mark.django_db
class TestLifecycleLockdown:
    """#6: runs are immutable history — the generic update/destroy verbs are
    closed so a run can't be re-pointed at another version or its audit trail
    deleted."""

    def test_instance_mutations_are_blocked(self):
        factory = APIRequestFactory()
        wf = Workflow.objects.create(name="ll", folder=Folder.get_root_folder())
        version = WorkflowVersion.objects.create(workflow=wf, run_as=publisher_user())
        instance = WorkflowInstance.objects.create(
            workflow=wf, version=version, folder=wf.folder
        )
        admin = publisher_user()
        for method, op in (("put", "update"), ("delete", "destroy")):
            view = WorkflowInstanceViewSet.as_view({method: op})
            req = getattr(factory, method)(
                f"/api/workflows/workflow-instances/{instance.id}/",
                {"version": str(version.id)},
                format="json",
            )
            force_authenticate(req, user=admin)
            resp = view(req, pk=str(instance.id))
            assert resp.status_code == 405, (op, resp.status_code)
        assert WorkflowInstance.objects.filter(id=instance.id).exists()


@pytest.mark.django_db
class TestNonRecursiveReadScope:
    """The read subtree scope must never grant more than the identity's own
    view scope: a non-recursive role assignment on the workflow's folder
    keeps descendant-domain rows out of read results."""

    def test_non_recursive_assignment_does_not_leak_subtree_rows(self):
        domain = make_domain("NR parent")
        child = Folder.objects.create(
            name="NR child",
            parent_folder=domain,
            content_type=Folder.ContentType.DOMAIN,
        )
        AppliedControl.objects.create(name="parent row", folder=domain)
        AppliedControl.objects.create(name="child row", folder=child)
        runner = User.objects.create_user(email="nonrecursive@authz.test")
        grant(
            runner,
            domain,
            ["view_appliedcontrol", "add_workflowinstance"],
            recursive=False,
        )

        workflow = Workflow.objects.create(name="NR read", folder=domain)
        version = WorkflowVersion.objects.create(workflow=workflow)
        trigger = node("trigger", trigger_config={"type": "manual"})
        read = node(
            "action",
            label="Fetch rows",
            action_config={"type": "read_objects", "model": "applied_control"},
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [trigger, read, end],
                "edges": [edge(trigger, read), edge(read, end)],
                "variables": [],
            },
        )
        publish_as(version, runner)

        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = instance.node_outputs["fetch_rows"]
        assert output["count"] == 1
        assert [row["name"] for row in output["results"]] == ["parent row"]
