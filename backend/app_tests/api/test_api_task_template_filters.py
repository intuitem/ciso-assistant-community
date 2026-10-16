"""
The occurrence filters on the task list must select what the matching columns show.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from core.models import TaskNode, TaskTemplate
from iam.models import Folder

URL = "/api/task-templates/"


def _one_time(folder, name, due, status):
    task = TaskTemplate.objects.create(
        name=name, folder=folder, is_recurrent=False, task_date=due
    )
    TaskNode.objects.create(
        task_template=task,
        due_date=due,
        scheduled_date=due,
        folder=folder,
        status=status,
    )
    return task


def _recurrent(folder, name, nodes):
    """nodes: (days from today, status) pairs."""
    today = timezone.localdate()
    task = TaskTemplate.objects.create(
        name=name,
        folder=folder,
        is_recurrent=True,
        task_date=today - timedelta(days=90),
        schedule={"frequency": "WEEKLY", "days_of_week": [0]},
    )
    for offset, status in nodes:
        due = today + timedelta(days=offset)
        TaskNode.objects.create(
            task_template=task,
            due_date=due,
            scheduled_date=due,
            folder=folder,
            status=status,
        )
    return task


@pytest.fixture
def tasks(db):
    folder = Folder.get_root_folder()
    for status in ("pending", "in_progress", "completed", "cancelled"):
        _one_time(
            folder, f"past_{status}", timezone.localdate() - timedelta(20), status
        )
        _one_time(
            folder, f"future_{status}", timezone.localdate() + timedelta(20), status
        )
    _recurrent(folder, "series_missed", [(-7, "pending"), (7, "pending")])
    _recurrent(folder, "series_on_track", [(-7, "completed"), (7, "in_progress")])


def _names(client, query=""):
    response = client.get(f"{URL}?{query}")
    assert response.status_code == 200, response.content
    return sorted(row["name"] for row in response.json()["results"])


@pytest.mark.django_db
class TestOccurrenceStatusFilters:
    @pytest.mark.parametrize(
        "status", ["pending", "in_progress", "completed", "cancelled"]
    )
    def test_next_status_filter_matches_column(
        self, authenticated_client, tasks, status
    ):
        rows = authenticated_client.get(URL).json()["results"]
        expected = sorted(
            row["name"] for row in rows if row["next_occurrence_status"] == status
        )
        assert expected
        assert _names(authenticated_client, f"next_occurrence_status={status}") == (
            expected
        )

    def test_next_status_keeps_past_one_time_tasks(self, authenticated_client, tasks):
        assert _names(authenticated_client, "next_occurrence_status=completed") == [
            "future_completed",
            "past_completed",
        ]

    def test_last_status_skips_one_time_tasks(self, authenticated_client, tasks):
        rows = authenticated_client.get(URL).json()["results"]
        expected = sorted(
            row["name"]
            for row in rows
            if row["last_occurrence_status"] in ("pending", "completed")
        )
        assert expected == ["series_missed", "series_on_track"]
        assert (
            _names(
                authenticated_client,
                "last_occurrence_status=pending&last_occurrence_status=completed",
            )
            == expected
        )


@pytest.mark.django_db
class TestOverdueFilter:
    def test_overdue(self, authenticated_client, tasks):
        assert _names(authenticated_client, "overdue=true") == [
            "past_in_progress",
            "past_pending",
            "series_missed",
        ]

    def test_analytics_overdue_matches_filter(self, authenticated_client, tasks):
        body = authenticated_client.get(f"{URL}analytics/").json()
        buckets = {b["key"]: b["count"] for b in body["due_buckets"]}
        assert buckets["overdue"] == len(_names(authenticated_client, "overdue=true"))
        # past_completed, past_cancelled, future_completed, future_cancelled
        assert buckets["closed"] == 4
        assert sum(buckets.values()) == body["count"]

    def test_analytics_old_start_date_is_not_overdue(self, authenticated_client, db):
        _recurrent(Folder.get_root_folder(), "series_finished", [(-7, "completed")])
        body = authenticated_client.get(f"{URL}analytics/").json()
        buckets = {b["key"]: b["count"] for b in body["due_buckets"]}
        assert buckets["overdue"] == 0
        assert buckets["no_eta"] == 1

    def test_not_overdue(self, authenticated_client, tasks):
        assert _names(authenticated_client, "overdue=false") == [
            "future_cancelled",
            "future_completed",
            "future_in_progress",
            "future_pending",
            "past_cancelled",
            "past_completed",
            "series_on_track",
        ]
