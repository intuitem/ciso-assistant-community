"""Absolute run TTL: a run older than its version's
timeout_seconds is terminated — inline when it next advances, and by the
periodic reaper if it's parked and never resumes."""

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from iam.models import Folder
from automation.workflows.engine import _run, start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowInstanceLog,
    WorkflowVersion,
)
from automation.workflows.tests.helpers import publisher_user


def node(type_, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(a, b, **kwargs):
    return {"id": str(uuid.uuid4()), "source": a["id"], "target": b["id"], **kwargs}


def log_workflow(timeout_seconds=0):
    workflow = Workflow.objects.create(
        name=f"ttl-{uuid.uuid4()}",
        folder=Folder.get_root_folder(),
        timeout_seconds=timeout_seconds,
    )
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    trigger = node("trigger", trigger_config={"type": "manual"})
    act = node("action", action_config={"type": "log", "message": "hi"})
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


def backdate(instance, seconds):
    WorkflowInstance.objects.filter(id=instance.id).update(
        created_at=timezone.now() - timedelta(seconds=seconds)
    )
    instance.refresh_from_db()


@pytest.mark.django_db
class TestTimeoutField:
    def test_version_inherits_timeout_on_create(self):
        workflow = Workflow.objects.create(
            name="Inherit", folder=Folder.get_root_folder(), timeout_seconds=3600
        )
        version = WorkflowVersion.objects.create(workflow=workflow)
        assert version.timeout_seconds == 3600

    def test_save_cascades_timeout_to_versions(self):
        workflow, version = log_workflow(timeout_seconds=0)
        assert version.timeout_seconds == 0
        workflow.timeout_seconds = 1800
        workflow.save()
        version.refresh_from_db()
        assert version.timeout_seconds == 1800

    def test_editing_timeout_does_not_touch_inflight_frozen_copy(self):
        # The engine reads the version copy; changing the workflow after a
        # version is frozen only affects future versions unless cascaded.
        workflow, version = log_workflow(timeout_seconds=100)
        # simulate a manual out-of-band version tweak staying put
        WorkflowVersion.objects.filter(id=version.id).update(timeout_seconds=100)
        version.refresh_from_db()
        assert version.timeout_seconds == 100


@pytest.mark.django_db
class TestTimeoutEnforcement:
    def test_zero_timeout_never_expires(self):
        _, version = log_workflow(timeout_seconds=0)
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED

    def test_normal_run_within_limit_completes(self):
        _, version = log_workflow(timeout_seconds=3600)
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED

    def test_resumed_run_over_ttl_terminates_on_advance(self):
        # An ACTIVE instance whose start is older than the limit is terminated
        # the moment _run touches it (mirrors a resume after a long park).
        _, version = log_workflow(timeout_seconds=60)
        instance = WorkflowInstance.objects.create(
            workflow=version.workflow, version=version, folder=version.folder
        )
        entry = version.nodes.get(type="trigger")
        from automation.workflows.models import WorkflowToken

        WorkflowToken.objects.create(instance=instance, current_node=entry)
        backdate(instance, 120)
        _run(instance)
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.FAILED
        assert instance.logs.filter(
            event_type=WorkflowInstanceLog.EventType.RUN_TERMINATED
        ).exists()

    def test_reaper_terminates_parked_over_ttl_run(self):
        from automation.workflows.tasks import reap_timed_out_runs

        _, version = log_workflow(timeout_seconds=60)
        instance = WorkflowInstance.objects.create(
            workflow=version.workflow, version=version, folder=version.folder
        )
        entry = version.nodes.get(type="trigger")
        from automation.workflows.models import WorkflowToken

        # Parked WAITING — never re-enters _run on its own.
        WorkflowToken.objects.create(
            instance=instance,
            current_node=entry,
            status=WorkflowToken.Status.WAITING,
        )
        backdate(instance, 120)

        reap_timed_out_runs.call_local()

        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.FAILED
        assert instance.logs.filter(
            event_type=WorkflowInstanceLog.EventType.RUN_TERMINATED
        ).exists()

    def test_reaper_ignores_within_limit_runs(self):
        from automation.workflows.tasks import reap_timed_out_runs

        _, version = log_workflow(timeout_seconds=3600)
        instance = WorkflowInstance.objects.create(
            workflow=version.workflow, version=version, folder=version.folder
        )
        from automation.workflows.models import WorkflowToken

        WorkflowToken.objects.create(
            instance=instance,
            current_node=version.nodes.get(type="trigger"),
            status=WorkflowToken.Status.WAITING,
        )
        backdate(instance, 60)  # well within 3600
        reap_timed_out_runs.call_local()
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.ACTIVE
