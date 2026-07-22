import uuid
from datetime import datetime, timedelta, timezone as dt_timezone

import pytest
from django.utils import timezone

from iam.models import Folder
from workflows.graph import save_graph
from workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowTrigger,
    WorkflowVersion,
)
from workflows.scheduling import (
    CronValidationError,
    next_occurrence,
    run_due_schedules,
    validate_cron_expression,
    validate_timezone,
)
from workflows.serializers import WorkflowTriggerWriteSerializer


def make_workflow(name="Scheduled flow", published=True, cron="*/10 * * * *"):
    """A workflow whose entry is a schedule trigger node; publishing creates
    the registration row (disabled by default per D22 arming policy)."""
    workflow = Workflow.objects.create(name=name, folder=Folder.get_root_folder())
    version = WorkflowVersion.objects.create(workflow=workflow)
    trigger = {
        "id": str(uuid.uuid4()),
        "type": "trigger",
        "ref": "nightly",
        "trigger_config": {"type": "schedule", "cron_expression": cron},
        "position": {},
    }
    log = {
        "id": str(uuid.uuid4()),
        "type": "action",
        "position": {},
        "action_config": {"type": "log", "message": "tick"},
    }
    end = {"id": str(uuid.uuid4()), "type": "end", "position": {}}
    save_graph(
        version,
        {
            "nodes": [trigger, log, end],
            "edges": [
                {
                    "id": str(uuid.uuid4()),
                    "source": trigger["id"],
                    "target": log["id"],
                },
                {"id": str(uuid.uuid4()), "source": log["id"], "target": end["id"]},
            ],
            "variables": [],
        },
    )
    if published:
        version.publish()
    return workflow, version


def get_registration(workflow, enabled=True):
    row = workflow.triggers.get(node_ref="nightly")
    if enabled and not row.enabled:
        serializer = WorkflowTriggerWriteSerializer(
            row, data={"enabled": True}, partial=True
        )
        assert serializer.is_valid(), serializer.errors
        row = serializer.save()
    return row


def force_due(registration, when=None):
    when = when or (timezone.now() - timedelta(minutes=1))
    WorkflowTrigger.objects.filter(id=registration.id).update(next_run_at=when)
    registration.refresh_from_db()


@pytest.fixture
def capture_runs(monkeypatch):
    calls = []
    monkeypatch.setattr("workflows.tasks.run_instance_task", calls.append)
    return calls


class TestCronValidation:
    def test_valid_expression(self):
        validate_cron_expression("0 3 * * *")
        validate_cron_expression("*/5 * * * *")
        # 1-minute floor: every-minute schedules are allowed
        validate_cron_expression("* * * * *")

    def test_invalid_expression(self):
        with pytest.raises(CronValidationError, match="invalidCronExpression"):
            validate_cron_expression("not a cron")

    def test_timezone(self):
        validate_timezone("Europe/Paris")
        with pytest.raises(CronValidationError, match="invalidTimezone"):
            validate_timezone("Mars/Olympus")

    def test_next_occurrence_respects_timezone(self):
        after = datetime(2026, 1, 15, 10, 0, tzinfo=dt_timezone.utc)
        # 03:00 in Paris (CET, UTC+1) is 02:00 UTC
        result = next_occurrence("0 3 * * *", "Europe/Paris", after)
        assert result == datetime(2026, 1, 16, 2, 0, tzinfo=dt_timezone.utc)

    def test_next_occurrence_invalid_expression(self):
        assert next_occurrence("bogus", "UTC", timezone.now()) is None


@pytest.mark.django_db
class TestRegistrationLifecycle:
    def test_publish_creates_disabled_registration(self):
        workflow, _ = make_workflow()
        row = workflow.triggers.get(node_ref="nightly")
        assert row.type == WorkflowTrigger.Type.SCHEDULE
        assert row.enabled is False
        assert row.next_run_at is None
        assert row.folder_id == workflow.folder_id

    def test_enable_computes_next_run_disable_clears_it(self):
        workflow, _ = make_workflow()
        row = get_registration(workflow)
        assert row.next_run_at is not None
        assert row.next_run_at > timezone.now()

        serializer = WorkflowTriggerWriteSerializer(
            row, data={"enabled": False}, partial=True
        )
        assert serializer.is_valid()
        row = serializer.save()
        assert row.next_run_at is None

    def test_republish_preserves_enabled_and_next_run(self):
        workflow, version = make_workflow()
        row = get_registration(workflow)
        before = row.next_run_at
        draft = version.clone_as_draft()
        draft.publish()
        row.refresh_from_db()
        assert row.enabled is True
        assert row.next_run_at == before

    def test_republish_with_new_cron_recomputes(self):
        workflow, version = make_workflow(cron="0 3 * * *")
        row = get_registration(workflow)
        before = row.next_run_at
        draft = version.clone_as_draft()
        node = draft.nodes.get(ref="nightly")
        node.trigger_config = {"type": "schedule", "cron_expression": "0 4 * * *"}
        node.save(update_fields=["trigger_config", "updated_at"])
        draft.publish()
        row.refresh_from_db()
        assert row.enabled is True
        assert row.next_run_at != before

    def test_removed_node_deletes_registration(self):
        workflow, version = make_workflow()
        draft = version.clone_as_draft()
        trigger_node = draft.nodes.get(ref="nightly")
        trigger_node.trigger_config = {"type": "manual"}
        trigger_node.ref = "manual_entry"
        trigger_node.save(update_fields=["trigger_config", "ref", "updated_at"])
        draft.publish()
        assert not workflow.triggers.filter(node_ref="nightly").exists()

    def test_subtype_change_resets_state_and_secret(self):
        workflow, version = make_workflow()
        row = get_registration(workflow)
        old_secret = row.secret
        draft = version.clone_as_draft()
        node = draft.nodes.get(ref="nightly")
        node.trigger_config = {"type": "webhook"}
        node.save(update_fields=["trigger_config", "updated_at"])
        draft.publish()
        row.refresh_from_db()
        assert row.type == WorkflowTrigger.Type.WEBHOOK
        assert row.enabled is True  # webhooks arrive live
        assert row.secret != old_secret
        assert row.next_run_at is None


@pytest.mark.django_db
class TestSchedulerTick:
    def test_due_schedule_fires(self, capture_runs):
        workflow, version = make_workflow()
        registration = get_registration(workflow)
        force_due(registration)
        started = run_due_schedules()
        assert len(started) == 1
        instance = started[0]
        assert instance.trigger == WorkflowInstance.Trigger.SCHEDULED
        assert instance.trigger_registration_id == registration.id
        assert instance.version_id == version.id
        assert capture_runs == [str(instance.id)]
        registration.refresh_from_db()
        assert registration.last_result == WorkflowTrigger.Result.TRIGGERED
        assert registration.next_run_at > timezone.now()

    def test_fires_at_the_schedule_trigger_branch(self, capture_runs):
        workflow, _ = make_workflow()
        registration = get_registration(workflow)
        force_due(registration)
        instance = run_due_schedules()[0]
        entry_log = instance.logs.filter(event_type="instance_started").get()
        assert entry_log.node.ref == "nightly"

    def test_not_due_schedule_ignored(self, capture_runs):
        workflow, _ = make_workflow()
        get_registration(workflow)
        assert run_due_schedules() == []
        assert capture_runs == []

    def test_disabled_registration_ignored(self, capture_runs):
        workflow, _ = make_workflow()
        registration = get_registration(workflow)
        force_due(registration)
        WorkflowTrigger.objects.filter(id=registration.id).update(enabled=False)
        assert run_due_schedules() == []

    def test_second_tick_is_noop(self, capture_runs):
        workflow, _ = make_workflow()
        registration = get_registration(workflow)
        force_due(registration)
        run_due_schedules()
        # first run finished; only dueness should gate the second tick
        WorkflowInstance.objects.update(status=WorkflowInstance.Status.COMPLETED)
        assert run_due_schedules() == []
        assert len(capture_runs) == 1

    def test_missed_occurrences_coalesce(self, capture_runs):
        workflow, _ = make_workflow(cron="*/10 * * * *")
        registration = get_registration(workflow)
        force_due(registration, timezone.now() - timedelta(days=3))
        started = run_due_schedules()
        assert len(started) == 1
        registration.refresh_from_db()
        assert registration.next_run_at > timezone.now()

    def test_overlap_skipped(self, capture_runs):
        workflow, _ = make_workflow()
        registration = get_registration(workflow)
        force_due(registration)
        run_due_schedules()
        # previous run still active -> next occurrence must skip, not queue
        force_due(registration)
        assert run_due_schedules() == []
        registration.refresh_from_db()
        assert registration.last_result == WorkflowTrigger.Result.SKIPPED_OVERLAP
        assert len(capture_runs) == 1

    def test_unpublished_workflow_skipped(self, capture_runs):
        # Registrations only exist for published graphs; archiving the
        # published version leaves the row pointing at nothing runnable.
        workflow, version = make_workflow()
        registration = get_registration(workflow)
        force_due(registration)
        WorkflowVersion.objects.filter(id=version.id).update(
            status=WorkflowVersion.Status.ARCHIVED
        )
        assert run_due_schedules() == []
        registration.refresh_from_db()
        assert registration.last_result == WorkflowTrigger.Result.SKIPPED_UNPUBLISHED
        assert capture_runs == []


@pytest.mark.django_db
class TestScheduleConfigValidation:
    """Cron/timezone validation moved from the schedule serializer to publish
    validation of the trigger node's config."""

    def _publish_errors(self, trigger_config):
        from workflows.validation import validate_graph

        workflow = Workflow.objects.create(
            name=f"cfg {uuid.uuid4().hex[:6]}", folder=Folder.get_root_folder()
        )
        version = WorkflowVersion.objects.create(workflow=workflow)
        trigger = {
            "id": str(uuid.uuid4()),
            "type": "trigger",
            "trigger_config": trigger_config,
            "position": {},
        }
        end = {"id": str(uuid.uuid4()), "type": "end", "position": {}}
        save_graph(
            version,
            {
                "nodes": [trigger, end],
                "edges": [
                    {
                        "id": str(uuid.uuid4()),
                        "source": trigger["id"],
                        "target": end["id"],
                    }
                ],
                "variables": [],
            },
        )
        return [e["code"] for e in validate_graph(version)]

    def test_rejects_invalid_cron(self):
        codes = self._publish_errors({"type": "schedule", "cron_expression": "nope"})
        assert "trigger_invalid_cron" in codes

    def test_accepts_every_minute_cron(self):
        codes = self._publish_errors(
            {"type": "schedule", "cron_expression": "* * * * *"}
        )
        assert codes == []

    def test_rejects_invalid_timezone(self):
        codes = self._publish_errors(
            {
                "type": "schedule",
                "cron_expression": "0 3 * * *",
                "timezone": "Mars/Olympus",
            }
        )
        assert "trigger_invalid_timezone" in codes

    def test_accepts_valid_config(self):
        codes = self._publish_errors(
            {
                "type": "schedule",
                "cron_expression": "0 3 * * *",
                "timezone": "Europe/Paris",
            }
        )
        assert codes == []

    def test_rejects_missing_trigger_type(self):
        codes = self._publish_errors({})
        assert "trigger_type_invalid" in codes
