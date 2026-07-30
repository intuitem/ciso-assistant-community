"""Workflow activation (spec D32): the master switch gates automatic
execution only, cascades to versions, and restore rebuilds drafts from
archived versions."""

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from iam.models import Folder, User
from workflows.engine import start_instance
from workflows.graph import save_graph
from workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowTrigger,
    WorkflowVersion,
)
from workflows.scheduling import run_due_schedules
from workflows.validation import validate_graph


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="activation_test@example.com", password="x"
    )


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


def build_workflow(name, trigger_config, publish=True):
    workflow = Workflow.objects.create(name=name, folder=Folder.get_root_folder())
    version = WorkflowVersion.objects.create(workflow=workflow)
    trigger = node("trigger", ref="entry", trigger_config=trigger_config)
    act = node("action", label="Log", action_config={"type": "log", "message": "hi"})
    end = node("end")
    save_graph(
        version,
        {
            "nodes": [trigger, act, end],
            "edges": [edge(trigger, act), edge(act, end)],
            "variables": [],
        },
    )
    if publish:
        version.publish()
    return workflow, version


@pytest.mark.django_db
class TestActivation:
    def test_disable_cascades_to_versions_and_reenable_restores(self):
        workflow, version = build_workflow("Cascade", {"type": "manual"})
        workflow.is_active = False
        workflow.save()
        version.refresh_from_db()
        assert version.is_active is False

        workflow.is_active = True
        workflow.save()
        version.refresh_from_db()
        assert version.is_active is True

    def test_manual_run_works_while_inactive(self):
        workflow, version = build_workflow("Manual ok", {"type": "manual"})
        workflow.is_active = False
        workflow.save()
        instance = start_instance(workflow.published_version)
        assert instance.status == WorkflowInstance.Status.COMPLETED

    def test_webhook_404s_while_inactive(self):
        workflow, _ = build_workflow("Hook off", {"type": "webhook"})
        workflow.is_active = False
        workflow.save()
        secret = workflow.triggers.get(node_ref="entry").secret
        resp = APIClient().post(
            f"/api/workflows/hooks/{workflow.id}/entry/{secret}/", {}, format="json"
        )
        assert resp.status_code == 404
        assert not workflow.instances.exists()

    def test_schedule_skips_inactive_and_advances(self):
        workflow, _ = build_workflow(
            "Cron off",
            {"type": "schedule", "cron_expression": "* * * * *", "timezone": "UTC"},
        )
        registration = workflow.triggers.get(node_ref="entry")
        registration.enabled = True
        registration.next_run_at = timezone.now() - timedelta(minutes=1)
        registration.save(update_fields=["enabled", "next_run_at"])
        workflow.is_active = False
        workflow.save()

        started = run_due_schedules()
        registration.refresh_from_db()
        assert started == []
        assert registration.last_result == WorkflowTrigger.Result.SKIPPED_INACTIVE
        assert registration.next_run_at > timezone.now()
        assert not workflow.instances.exists()

    def test_subprocess_into_inactive_child_fails_parent(self):
        child, _ = build_workflow("Paused child", {"type": "manual"})
        child.is_active = False
        child.save()

        parent = Workflow.objects.create(
            name="Parent", folder=Folder.get_root_folder()
        )
        version = WorkflowVersion.objects.create(workflow=parent)
        trigger = node("trigger", trigger_config={"type": "manual"})
        sub = node("subprocess", label="Call child", subprocess_workflow=str(child.id))
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [trigger, sub, end],
                "edges": [edge(trigger, sub), edge(sub, end)],
                "variables": [],
            },
        )
        codes = [e["code"] for e in validate_graph(version)]
        assert "subprocess_inactive" in codes

        instance = start_instance(version)
        assert instance.status != WorkflowInstance.Status.COMPLETED
        assert any(
            "inactive" in (log.message or "")
            for log in instance.logs.filter(event_type="error")
        )


@pytest.mark.django_db
class TestRestore:
    def _workflow_with_archived_version(self):
        workflow, v1 = build_workflow("Restorable", {"type": "manual"})
        draft = v1.clone_as_draft()
        draft.publish()  # v1 becomes archived, v2 published
        v1.refresh_from_db()
        assert v1.status == WorkflowVersion.Status.ARCHIVED
        return workflow, v1

    def test_restore_archived_creates_draft(self, superuser):
        workflow, archived = self._workflow_with_archived_version()
        client = APIClient()
        client.force_authenticate(superuser)
        resp = client.post(f"/api/workflows/workflow-versions/{archived.id}/restore/")
        assert resp.status_code == 201, resp.data
        assert workflow.draft_version is not None
        assert workflow.draft_version.version_number == 3

    def test_restore_blocked_when_draft_exists(self, superuser):
        workflow, archived = self._workflow_with_archived_version()
        workflow.published_version.clone_as_draft()
        client = APIClient()
        client.force_authenticate(superuser)
        resp = client.post(f"/api/workflows/workflow-versions/{archived.id}/restore/")
        assert resp.status_code == 400
        assert resp.data["error"] == "draftAlreadyExists"

    def test_restore_rejects_non_archived(self, superuser):
        workflow, _ = self._workflow_with_archived_version()
        published = workflow.published_version
        client = APIClient()
        client.force_authenticate(superuser)
        resp = client.post(f"/api/workflows/workflow-versions/{published.id}/restore/")
        assert resp.status_code == 400
        assert resp.data["error"] == "onlyArchivedVersionsCanBeRestored"
