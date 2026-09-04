"""
Tests for TaskNode reliability: conservative GC, rescheduling preservation,
materialization via the calendar endpoint, and TaskTemplate.save() pruning.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from core.models import Evidence, EvidenceRevision, TaskNode, TaskTemplate
from core.views import TaskTemplateViewSet
from iam.models import Folder

# ── Constants ──────────────────────────────────────────────────────────────

TASK_TEMPLATE_NAME = "Test Task Template"
TASK_TEMPLATE_DESCRIPTION = "Test Description"

WEEKLY_SCHEDULE = {
    "frequency": "WEEKLY",
    "days_of_week": [0],  # Monday
}


def _next_monday():
    """Return the next Monday on or after today."""
    today = timezone.localdate()
    days_ahead = (0 - today.weekday()) % 7  # 0 = Monday
    if days_ahead == 0:
        days_ahead = 7  # always pick a future Monday
    return today + timedelta(days=days_ahead)


def _make_weekly_template(folder, start_date, end_date=None, name=None):
    """Helper: create a recurrent weekly task template."""
    schedule = {**WEEKLY_SCHEDULE}
    if end_date:
        schedule["end_date"] = str(end_date)
    return TaskTemplate.objects.create(
        name=name or TASK_TEMPLATE_NAME,
        description=TASK_TEMPLATE_DESCRIPTION,
        folder=folder,
        is_recurrent=True,
        task_date=start_date,
        schedule=schedule,
    )


def _calendar_url(start, end):
    return f"/api/task-templates/calendar/{start}/{end}/"


# ── Calendar materialization ──────────────────────────────────────────────


@pytest.mark.django_db
class TestTaskCalendarMaterialization:
    """Verify that the calendar endpoint creates TaskNode records."""

    def test_calendar_materializes_nodes(self, authenticated_client):
        """Virtual occurrences become real TaskNode rows."""
        folder = Folder.get_root_folder()
        start = _next_monday()
        template = _make_weekly_template(folder, start)

        end = start + timedelta(weeks=4)
        response = authenticated_client.get(_calendar_url(start, end))

        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) >= 4

        # All returned tasks should be backed by real DB nodes
        node_count = TaskNode.objects.filter(task_template=template).count()
        assert node_count >= 4

    def test_calendar_no_duplicates_on_repeated_calls(self, authenticated_client):
        """Calling the calendar twice should not create duplicate nodes."""
        folder = Folder.get_root_folder()
        start = _next_monday()
        template = _make_weekly_template(folder, start)
        end = start + timedelta(weeks=4)

        authenticated_client.get(_calendar_url(start, end))
        count_after_first = TaskNode.objects.filter(task_template=template).count()

        authenticated_client.get(_calendar_url(start, end))
        count_after_second = TaskNode.objects.filter(task_template=template).count()

        assert count_after_first == count_after_second


# ── Conservative GC ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestConservativeGarbageCollection:
    """GC should only delete truly untouched pending nodes."""

    def test_gc_preserves_in_progress_node(self, authenticated_client):
        """A node marked in_progress must survive GC."""
        folder = Folder.get_root_folder()
        start = _next_monday()
        end = start + timedelta(weeks=4)
        template = _make_weekly_template(folder, start)

        # Materialize nodes
        authenticated_client.get(_calendar_url(start, end))

        # Mark one as in_progress
        node = TaskNode.objects.filter(task_template=template).first()
        node.status = "in_progress"
        node.save(update_fields=["status"])
        node_id = node.id

        # Update template schedule to trigger _sync_task_nodes
        authenticated_client.patch(
            f"/api/task-templates/{template.id}/",
            {"schedule": {**WEEKLY_SCHEDULE, "days_of_week": [1]}},  # Tuesday
            format="json",
        )

        assert TaskNode.objects.filter(id=node_id).exists(), (
            "In-progress node was deleted by GC"
        )

    def test_gc_preserves_node_with_observation(self, authenticated_client):
        """A node with an observation must survive GC."""
        folder = Folder.get_root_folder()
        start = _next_monday()
        end = start + timedelta(weeks=4)
        template = _make_weekly_template(folder, start)

        authenticated_client.get(_calendar_url(start, end))

        node = TaskNode.objects.filter(task_template=template).first()
        node.observation = "Some important note"
        node.save(update_fields=["observation"])
        node_id = node.id

        authenticated_client.patch(
            f"/api/task-templates/{template.id}/",
            {"schedule": {**WEEKLY_SCHEDULE, "days_of_week": [1]}},
            format="json",
        )

        assert TaskNode.objects.filter(id=node_id).exists(), (
            "Node with observation was deleted by GC"
        )

    def test_gc_preserves_node_with_evidence(self, authenticated_client):
        """A node with attached evidence must survive GC."""
        folder = Folder.get_root_folder()
        start = _next_monday()
        end = start + timedelta(weeks=4)
        template = _make_weekly_template(folder, start)

        authenticated_client.get(_calendar_url(start, end))

        node = TaskNode.objects.filter(task_template=template).first()
        evidence = Evidence.objects.create(name="test evidence", folder=folder)
        node.evidences.add(evidence)
        node_id = node.id

        authenticated_client.patch(
            f"/api/task-templates/{template.id}/",
            {"schedule": {**WEEKLY_SCHEDULE, "days_of_week": [1]}},
            format="json",
        )

        assert TaskNode.objects.filter(id=node_id).exists(), (
            "Node with evidence was deleted by GC"
        )

    def test_gc_preserves_node_with_evidence_revision(self, authenticated_client):
        """A node with an evidence revision must survive GC."""
        folder = Folder.get_root_folder()
        start = _next_monday()
        end = start + timedelta(weeks=4)
        template = _make_weekly_template(folder, start)

        authenticated_client.get(_calendar_url(start, end))

        node = TaskNode.objects.filter(task_template=template).first()
        evidence = Evidence.objects.create(name="test evidence", folder=folder)
        EvidenceRevision.objects.create(
            evidence=evidence, task_node=node, folder=folder
        )
        node_id = node.id

        authenticated_client.patch(
            f"/api/task-templates/{template.id}/",
            {"schedule": {**WEEKLY_SCHEDULE, "days_of_week": [1]}},
            format="json",
        )

        assert TaskNode.objects.filter(id=node_id).exists(), (
            "Node with evidence revision was deleted by GC"
        )

    def test_gc_deletes_untouched_pending_node(self, authenticated_client):
        """A pristine pending node whose slot is removed should be deleted."""
        folder = Folder.get_root_folder()
        start = _next_monday()
        end = start + timedelta(weeks=4)
        template = _make_weekly_template(folder, start)

        authenticated_client.get(_calendar_url(start, end))
        initial_count = TaskNode.objects.filter(task_template=template).count()
        assert initial_count >= 4

        # Change schedule — old Monday slots are no longer generated
        authenticated_client.patch(
            f"/api/task-templates/{template.id}/",
            {"schedule": {**WEEKLY_SCHEDULE, "days_of_week": [1]}},
            format="json",
        )

        # Old untouched nodes for Mondays should be gone
        remaining = TaskNode.objects.filter(
            task_template=template, status="pending"
        ).count()
        # New Tuesday slots may have been created, but old Monday pristine
        # nodes should have been cleaned up
        monday_nodes = TaskNode.objects.filter(
            task_template=template,
            scheduled_date__week_day=2,  # Django: Sunday=1, Monday=2
        ).count()
        assert monday_nodes == 0, "Untouched Monday nodes were not GC'd"


# ── Rescheduling preservation ─────────────────────────────────────────────


@pytest.mark.django_db
class TestReschedulingPreservation:
    """Nodes rescheduled by the user (due_date != scheduled_date) must survive."""

    def test_rescheduled_node_survives_sync(self, authenticated_client):
        """A user-rescheduled node must not be deleted on schedule sync."""
        folder = Folder.get_root_folder()
        start = _next_monday()
        end = start + timedelta(weeks=4)
        template = _make_weekly_template(folder, start)

        authenticated_client.get(_calendar_url(start, end))

        # Reschedule a node
        node = TaskNode.objects.filter(task_template=template).first()
        original_scheduled = node.scheduled_date
        new_due = original_scheduled + timedelta(days=2)
        node.due_date = new_due
        node.save(update_fields=["due_date"])
        node_id = node.id

        # Trigger sync
        authenticated_client.patch(
            f"/api/task-templates/{template.id}/",
            {"name": "Updated Name"},
            format="json",
        )

        node = TaskNode.objects.get(id=node_id)
        assert node.due_date == new_due, "Rescheduled due_date was overwritten"
        assert node.scheduled_date == original_scheduled

    def test_rescheduled_node_appears_in_calendar(self, authenticated_client):
        """A rescheduled node should appear in the calendar at its new due_date."""
        folder = Folder.get_root_folder()
        start = _next_monday()
        end = start + timedelta(weeks=4)
        template = _make_weekly_template(folder, start)

        authenticated_client.get(_calendar_url(start, end))

        node = TaskNode.objects.filter(task_template=template).earliest(
            "scheduled_date"
        )
        new_due = node.scheduled_date + timedelta(days=3)
        node.due_date = new_due
        node.save(update_fields=["due_date"])
        node_id = str(node.id)

        response = authenticated_client.get(_calendar_url(start, end))
        tasks = response.json()

        task_ids = [str(t.get("id")) for t in tasks]
        assert node_id in task_ids, "Rescheduled node not found in calendar response"


# ── TaskTemplate.save() pruning ───────────────────────────────────────────


@pytest.mark.django_db
class TestTaskTemplateSavePruning:
    """TaskTemplate.save() should prune only untouched nodes beyond end_date."""

    def test_prune_respects_end_date(self, authenticated_client):
        """Nodes beyond the schedule end_date should be pruned if untouched."""
        folder = Folder.get_root_folder()
        start = _next_monday()
        far_end = start + timedelta(weeks=12)
        template = _make_weekly_template(folder, start, end_date=far_end)

        # Materialize nodes
        authenticated_client.get(_calendar_url(start, far_end))
        total_before = TaskNode.objects.filter(task_template=template).count()
        assert total_before > 0

        # Shorten the schedule end_date
        new_end = start + timedelta(weeks=4)
        template.schedule["end_date"] = str(new_end)
        template.save()

        beyond_end = TaskNode.objects.filter(
            task_template=template,
            scheduled_date__gt=new_end,
            status="pending",
        ).count()
        assert beyond_end == 0, "Untouched nodes beyond end_date were not pruned"

    def test_prune_preserves_completed_node_beyond_end(self, authenticated_client):
        """Completed nodes beyond the end_date must NOT be pruned."""
        folder = Folder.get_root_folder()
        start = _next_monday()
        far_end = start + timedelta(weeks=12)
        template = _make_weekly_template(folder, start, end_date=far_end)

        authenticated_client.get(_calendar_url(start, far_end))

        # Mark a future node as completed
        future_node = TaskNode.objects.filter(
            task_template=template,
            scheduled_date__gt=start + timedelta(weeks=6),
        ).first()
        assert future_node is not None
        future_node.status = "completed"
        future_node.save(update_fields=["status"])
        node_id = future_node.id

        # Shorten the schedule
        new_end = start + timedelta(weeks=4)
        template.schedule["end_date"] = str(new_end)
        template.save()

        assert TaskNode.objects.filter(id=node_id).exists(), (
            "Completed node beyond end_date was incorrectly pruned"
        )


# ── Sync horizon ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSyncHorizon:
    """The materialization horizon scales with the period, not the frequency."""

    @pytest.mark.parametrize(
        "frequency,interval",
        [
            ("DAILY", 1),
            ("DAILY", 30),
            ("WEEKLY", 1),
            ("MONTHLY", 1),
            ("MONTHLY", 3),
            ("YEARLY", 1),
            ("YEARLY", 10),
        ],
    )
    def test_node_count_is_bounded_regardless_of_frequency(
        self, authenticated_client, frequency, interval
    ):
        """A daily task and a ten-yearly one cost the same handful of rows."""
        response = authenticated_client.post(
            "/api/task-templates/",
            {
                "name": f"{frequency}-{interval}",
                "folder": str(Folder.get_root_folder().id),
                "is_recurrent": True,
                "schedule": {"frequency": frequency, "interval": interval},
            },
            format="json",
        )
        assert response.status_code == 201
        count = TaskNode.objects.filter(task_template_id=response.json()["id"]).count()
        assert 1 <= count <= TaskTemplateViewSet.SYNC_AHEAD_OCCURRENCES + 1, (
            f"{frequency}/{interval} materialized {count} nodes"
        )

    def test_horizon_stops_at_recurrence_end_date(self):
        today = timezone.localdate()
        end = today + timedelta(days=5)
        assert (
            TaskTemplateViewSet._sync_end_date(
                {"frequency": "MONTHLY", "interval": 1, "end_date": str(end)}, today
            )
            == end
        )

    def test_horizon_is_capped_for_very_long_periods(self):
        today = timezone.localdate()
        assert (
            TaskTemplateViewSet._sync_end_date(
                {"frequency": "YEARLY", "interval": 10}, today
            )
            == today + TaskTemplateViewSet.SYNC_HORIZON_CAP
        )

    def test_horizon_tolerates_schedule_without_interval(self):
        today = timezone.localdate()
        assert TaskTemplateViewSet._sync_end_date(
            {"frequency": "WEEKLY", "days_of_week": [0]}, today
        ) == today + timedelta(weeks=TaskTemplateViewSet.SYNC_AHEAD_OCCURRENCES)


# ── Disabled templates ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDisabledTemplate:
    """A disabled template must not generate occurrences."""

    def test_disabled_template_generates_no_nodes(self, authenticated_client):
        response = authenticated_client.post(
            "/api/task-templates/",
            {
                "name": "Retired control",
                "folder": str(Folder.get_root_folder().id),
                "is_recurrent": True,
                "enabled": False,
                "schedule": {"frequency": "MONTHLY", "interval": 1},
            },
            format="json",
        )
        assert response.status_code == 201
        assert (
            TaskNode.objects.filter(task_template_id=response.json()["id"]).count() == 0
        )

    def test_disabling_retires_pending_future_nodes(self, authenticated_client):
        folder = Folder.get_root_folder()
        start = _next_monday()
        template = _make_weekly_template(folder, start)
        authenticated_client.get(_calendar_url(start, start + timedelta(weeks=4)))
        assert TaskNode.objects.filter(task_template=template).count() > 0

        authenticated_client.patch(
            f"/api/task-templates/{template.id}/",
            {"enabled": False},
            format="json",
        )

        assert (
            TaskNode.objects.filter(
                task_template=template, status="pending", due_date__gte=start
            ).count()
            == 0
        )

    def test_disabling_preserves_completed_nodes(self, authenticated_client):
        folder = Folder.get_root_folder()
        start = _next_monday()
        template = _make_weekly_template(folder, start)
        authenticated_client.get(_calendar_url(start, start + timedelta(weeks=4)))

        node = TaskNode.objects.filter(task_template=template).first()
        node.status = "completed"
        node.save(update_fields=["status"])

        authenticated_client.patch(
            f"/api/task-templates/{template.id}/",
            {"enabled": False},
            format="json",
        )

        assert TaskNode.objects.filter(id=node.id).exists()
