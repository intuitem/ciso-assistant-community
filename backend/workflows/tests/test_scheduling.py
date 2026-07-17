import uuid
from datetime import datetime, timedelta, timezone as dt_timezone

import pytest
from django.utils import timezone

from iam.models import Folder
from workflows.graph import save_graph
from workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowSchedule,
    WorkflowVersion,
)
from workflows.scheduling import (
    CronValidationError,
    next_occurrence,
    run_due_schedules,
    validate_cron_expression,
    validate_timezone,
)
from workflows.serializers import WorkflowScheduleWriteSerializer


def make_workflow(name="Scheduled flow", published=True):
    workflow = Workflow.objects.create(name=name, folder=Folder.get_root_folder())
    version = WorkflowVersion.objects.create(workflow=workflow)
    start = {"id": str(uuid.uuid4()), "type": "start", "position": {}}
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
            "nodes": [start, log, end],
            "edges": [
                {"id": str(uuid.uuid4()), "source": start["id"], "target": log["id"]},
                {"id": str(uuid.uuid4()), "source": log["id"], "target": end["id"]},
            ],
            "variables": [],
        },
    )
    if published:
        version.publish()
    return workflow, version


def make_schedule(workflow, name="nightly", cron="*/10 * * * *", **kwargs):
    return WorkflowSchedule.objects.create(
        name=name, workflow=workflow, cron_expression=cron, **kwargs
    )


def force_due(schedule, when=None):
    """Backdate next_run_at without triggering save()'s recompute."""
    when = when or (timezone.now() - timedelta(minutes=1))
    WorkflowSchedule.objects.filter(id=schedule.id).update(next_run_at=when)
    schedule.refresh_from_db()


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
class TestScheduleModel:
    def test_save_computes_next_run(self):
        workflow, _ = make_workflow()
        schedule = make_schedule(workflow)
        assert schedule.next_run_at is not None
        assert schedule.next_run_at > timezone.now()

    def test_disable_clears_next_run_and_reenable_recomputes(self):
        workflow, _ = make_workflow()
        schedule = make_schedule(workflow)
        schedule.enabled = False
        schedule.save()
        assert schedule.next_run_at is None
        schedule.enabled = True
        schedule.save()
        assert schedule.next_run_at is not None

    def test_cron_change_recomputes(self):
        workflow, _ = make_workflow()
        schedule = make_schedule(workflow, cron="0 3 * * *")
        before = schedule.next_run_at
        schedule.cron_expression = "0 4 * * *"
        schedule.save()
        assert schedule.next_run_at != before

    def test_save_without_change_keeps_claimed_next_run(self):
        workflow, _ = make_workflow()
        schedule = make_schedule(workflow)
        force_due(schedule)
        claimed = schedule.next_run_at
        schedule.description = "edited"
        schedule.save()
        assert schedule.next_run_at == claimed

    def test_folder_follows_workflow(self):
        workflow, _ = make_workflow()
        schedule = make_schedule(workflow)
        assert schedule.folder_id == workflow.folder_id


@pytest.mark.django_db
class TestSchedulerTick:
    def test_due_schedule_fires(self, capture_runs):
        workflow, version = make_workflow()
        schedule = make_schedule(workflow)
        force_due(schedule)
        started = run_due_schedules()
        assert len(started) == 1
        instance = started[0]
        assert instance.trigger == WorkflowInstance.Trigger.SCHEDULED
        assert instance.schedule_id == schedule.id
        assert instance.version_id == version.id
        assert capture_runs == [str(instance.id)]
        schedule.refresh_from_db()
        assert schedule.last_result == WorkflowSchedule.Result.TRIGGERED
        assert schedule.next_run_at > timezone.now()

    def test_not_due_schedule_ignored(self, capture_runs):
        workflow, _ = make_workflow()
        make_schedule(workflow)
        assert run_due_schedules() == []
        assert capture_runs == []

    def test_disabled_schedule_ignored(self, capture_runs):
        workflow, _ = make_workflow()
        schedule = make_schedule(workflow)
        force_due(schedule)
        WorkflowSchedule.objects.filter(id=schedule.id).update(enabled=False)
        assert run_due_schedules() == []

    def test_second_tick_is_noop(self, capture_runs):
        workflow, _ = make_workflow()
        schedule = make_schedule(workflow)
        force_due(schedule)
        run_due_schedules()
        # first run finished; only dueness should gate the second tick
        WorkflowInstance.objects.update(status=WorkflowInstance.Status.COMPLETED)
        assert run_due_schedules() == []
        assert len(capture_runs) == 1

    def test_missed_occurrences_coalesce(self, capture_runs):
        workflow, _ = make_workflow()
        schedule = make_schedule(workflow, cron="*/10 * * * *")
        force_due(schedule, timezone.now() - timedelta(days=3))
        started = run_due_schedules()
        assert len(started) == 1
        schedule.refresh_from_db()
        assert schedule.next_run_at > timezone.now()

    def test_overlap_skipped(self, capture_runs):
        workflow, _ = make_workflow()
        schedule = make_schedule(workflow)
        force_due(schedule)
        run_due_schedules()
        # previous run still active -> next occurrence must skip, not queue
        force_due(schedule)
        assert run_due_schedules() == []
        schedule.refresh_from_db()
        assert schedule.last_result == WorkflowSchedule.Result.SKIPPED_OVERLAP
        assert len(capture_runs) == 1

    def test_unpublished_workflow_skipped(self, capture_runs):
        workflow, _ = make_workflow(published=False)
        schedule = make_schedule(workflow)
        force_due(schedule)
        assert run_due_schedules() == []
        schedule.refresh_from_db()
        assert schedule.last_result == WorkflowSchedule.Result.SKIPPED_UNPUBLISHED
        assert capture_runs == []


@pytest.mark.django_db
class TestScheduleSerializer:
    def test_rejects_invalid_cron(self):
        workflow, _ = make_workflow()
        serializer = WorkflowScheduleWriteSerializer(
            data={
                "name": "bad",
                "workflow": str(workflow.id),
                "cron_expression": "nope",
            }
        )
        assert not serializer.is_valid()
        assert "cron_expression" in serializer.errors

    def test_accepts_every_minute_cron(self):
        workflow, _ = make_workflow()
        serializer = WorkflowScheduleWriteSerializer(
            data={
                "name": "every-minute",
                "workflow": str(workflow.id),
                "cron_expression": "* * * * *",
            }
        )
        assert serializer.is_valid(), serializer.errors

    def test_rejects_invalid_timezone(self):
        workflow, _ = make_workflow()
        serializer = WorkflowScheduleWriteSerializer(
            data={
                "name": "bad-tz",
                "workflow": str(workflow.id),
                "cron_expression": "0 3 * * *",
                "timezone": "Mars/Olympus",
            }
        )
        assert not serializer.is_valid()
        assert "timezone" in serializer.errors

    def test_accepts_valid_payload(self):
        workflow, _ = make_workflow()
        serializer = WorkflowScheduleWriteSerializer(
            data={
                "name": "nightly",
                "workflow": str(workflow.id),
                "cron_expression": "0 3 * * *",
                "timezone": "Europe/Paris",
            }
        )
        assert serializer.is_valid(), serializer.errors
