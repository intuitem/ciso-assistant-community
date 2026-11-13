"""
Tests for the control plan endpoint (task-templates/yearly_review): bucket
generation per granularity and the overdue flag.
"""

import uuid
from datetime import date, timedelta

import pytest
from django.utils import timezone
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.models import AppliedControl, TaskNode, TaskTemplate
from core.utils import RoleCodename
from core.views import TaskTemplateViewSet
from iam.models import Folder, Role, RoleAssignment, User

REVIEW_URL = "/api/task-templates/yearly_review/"


def _make_template(name="Control plan task"):
    folder = Folder.get_root_folder()
    return TaskTemplate.objects.create(
        name=name,
        folder=folder,
        is_recurrent=True,
        task_date=date(2020, 1, 1),
        schedule={"interval": 1, "frequency": "MONTHLY"},
    )


def _make_node(template, due_date, status="pending"):
    return TaskNode.objects.create(
        task_template=template,
        folder=template.folder,
        due_date=due_date,
        scheduled_date=due_date,
        status=status,
    )


def _review(client, **params):
    response = client.get(REVIEW_URL, params)
    assert response.status_code == 200
    return response.json()


def _window(*days):
    """Query params for the months spanning the given days."""
    first, last = min(days), max(days)
    return {
        "start_month": first.month,
        "start_year": first.year,
        "end_month": last.month,
        "end_year": last.year,
    }


def _task(payload, template):
    tasks = [task for folder in payload["folders"] for task in folder["tasks"]]
    return next(task for task in tasks if task["id"] == str(template.id))


class TestBuckets:
    """Bucket generation is pure date arithmetic: no database needed."""

    def test_monthly_buckets_keep_their_keys(self):
        buckets = TaskTemplateViewSet._generate_buckets(
            date(2026, 11, 1), date(2027, 1, 31), "monthly"
        )
        assert [b["key"] for b in buckets] == ["2026-11", "2026-12", "2027-01"]
        assert buckets[0]["start"] == "2026-11-01"
        assert buckets[0]["end"] == "2026-11-30"

    def test_quarterly_buckets(self):
        buckets = TaskTemplateViewSet._generate_buckets(
            date(2026, 1, 1), date(2026, 12, 31), "quarterly"
        )
        assert [b["key"] for b in buckets] == [
            "2026-Q1",
            "2026-Q2",
            "2026-Q3",
            "2026-Q4",
        ]
        assert (buckets[1]["start"], buckets[1]["end"]) == ("2026-04-01", "2026-06-30")

    def test_semiannual_buckets(self):
        buckets = TaskTemplateViewSet._generate_buckets(
            date(2026, 7, 1), date(2027, 6, 30), "semiannual"
        )
        assert [b["key"] for b in buckets] == ["2026-H2", "2027-H1"]
        assert (buckets[0]["start"], buckets[0]["end"]) == ("2026-07-01", "2026-12-31")

    @pytest.mark.parametrize(
        "day, granularity, key",
        [
            (date(2026, 5, 17), "monthly", "2026-05"),
            (date(2026, 5, 17), "quarterly", "2026-Q2"),
            (date(2026, 5, 17), "semiannual", "2026-H1"),
            (date(2026, 12, 31), "quarterly", "2026-Q4"),
            (date(2026, 7, 1), "semiannual", "2026-H2"),
        ],
    )
    def test_bucket_key(self, day, granularity, key):
        assert TaskTemplateViewSet._assign_node_to_bucket_key(day, granularity) == key


@pytest.mark.django_db
class TestGranularity:
    def test_quarterly_range_widens_to_whole_quarters(self, authenticated_client):
        """A range cutting through a quarter still reports the whole quarter."""
        template = _make_template()
        _make_node(template, date(2026, 4, 2), status="completed")

        payload = _review(
            authenticated_client,
            start_month=5,
            start_year=2026,
            end_month=8,
            end_year=2026,
            granularity="quarterly",
        )

        assert payload["granularity"] == "quarterly"
        assert [b["key"] for b in payload["buckets"]] == ["2026-Q2", "2026-Q3"]
        assert payload["buckets"][0]["start"] == "2026-04-01"
        assert payload["buckets"][-1]["end"] == "2026-09-30"
        status = _task(payload, template)["bucket_status"]
        assert status["2026-Q2"]["status"] == "completed"
        assert status["2026-Q3"]["status"] is None

    def test_semiannual_groups_six_months(self, authenticated_client):
        template = _make_template()
        _make_node(template, date(2026, 2, 10), status="completed")
        _make_node(template, date(2026, 6, 10), status="completed")

        payload = _review(
            authenticated_client,
            start_month=1,
            start_year=2026,
            end_month=12,
            end_year=2026,
            granularity="semiannual",
        )

        assert [b["key"] for b in payload["buckets"]] == ["2026-H1", "2026-H2"]
        first_half = _task(payload, template)["bucket_status"]["2026-H1"]
        assert first_half["status"] == "completed"
        assert len(first_half["node_ids"]) == 2

    def test_unknown_granularity_falls_back_to_monthly(self, authenticated_client):
        payload = _review(authenticated_client, granularity="fortnightly")
        assert payload["granularity"] == "monthly"


@pytest.mark.django_db
class TestOverdue:
    def test_open_occurrence_past_due_is_overdue(self, authenticated_client):
        today = timezone.localdate()
        late, upcoming = today - timedelta(days=40), today + timedelta(days=40)
        template = _make_template()
        _make_node(template, late, status="pending")
        _make_node(template, upcoming, status="pending")

        payload = _review(authenticated_client, **_window(late, upcoming))
        status = _task(payload, template)["bucket_status"]

        late_bucket = status[f"{late.year}-{late.month:02d}"]
        upcoming_bucket = status[f"{upcoming.year}-{upcoming.month:02d}"]
        late_ids = [str(n.id) for n in template.tasknode_set.filter(due_date=late)]
        assert late_bucket == {
            "status": "pending",
            "node_ids": late_ids,
            "overdue": True,
            "overdue_node_id": late_ids[0],
        }
        assert upcoming_bucket["overdue_node_id"] is None
        assert payload["today"] == today.isoformat()
        assert upcoming_bucket["status"] == "pending"
        assert upcoming_bucket["overdue"] is False

    def test_overdue_bucket_names_its_late_occurrence(self, authenticated_client):
        # A quarter whose first occurrence is closed and a later one is late:
        # the cell must lead to the late one.
        today = timezone.localdate()
        quarter_start = date(today.year - 1, 1, 1)
        template = _make_template()
        _make_node(template, quarter_start + timedelta(days=5), status="completed")
        late = _make_node(template, quarter_start + timedelta(days=40))
        _make_node(template, quarter_start + timedelta(days=70))

        payload = _review(
            authenticated_client,
            **_window(quarter_start, quarter_start + timedelta(days=70)),
            granularity="quarterly",
        )
        bucket = _task(payload, template)["bucket_status"][f"{quarter_start.year}-Q1"]

        assert bucket["overdue"] is True
        assert bucket["overdue_node_id"] == str(late.id)
        assert bucket["node_ids"][0] != str(late.id)

    def test_in_progress_past_due_is_overdue(self, authenticated_client):
        late = timezone.localdate() - timedelta(days=40)
        template = _make_template()
        _make_node(template, late, status="in_progress")

        payload = _review(authenticated_client, **_window(late))
        bucket = _task(payload, template)["bucket_status"][
            f"{late.year}-{late.month:02d}"
        ]
        assert bucket["status"] == "in_progress"
        assert bucket["overdue"] is True

    @pytest.mark.parametrize("status", ["completed", "cancelled"])
    def test_closed_occurrence_is_never_overdue(self, authenticated_client, status):
        late = timezone.localdate() - timedelta(days=40)
        template = _make_template()
        _make_node(template, late, status=status)

        payload = _review(authenticated_client, **_window(late))
        bucket = _task(payload, template)["bucket_status"][
            f"{late.year}-{late.month:02d}"
        ]
        assert bucket["overdue"] is False

    def test_due_today_is_not_overdue(self, authenticated_client):
        today = timezone.localdate()
        template = _make_template()
        _make_node(template, today, status="pending")

        payload = _review(authenticated_client, **_window(today))
        bucket = _task(payload, template)["bucket_status"][
            f"{today.year}-{today.month:02d}"
        ]
        assert bucket["overdue"] is False

    def test_overdue_status_filter(self, authenticated_client):
        today = timezone.localdate()
        late, upcoming = today - timedelta(days=40), today + timedelta(days=40)
        late_template = _make_template(name="Late task")
        _make_node(late_template, late, status="pending")
        on_time_template = _make_template(name="On time task")
        _make_node(on_time_template, late, status="completed")
        _make_node(on_time_template, upcoming, status="pending")

        payload = _review(
            authenticated_client, status="overdue", **_window(late, upcoming)
        )
        ids = {task["id"] for folder in payload["folders"] for task in folder["tasks"]}
        assert ids == {str(late_template.id)}


@pytest.mark.django_db
class TestLateOutsideThePeriod:
    """Open occurrences late today but outside the displayed range are still late."""

    def test_late_before_the_period(self, authenticated_client):
        today = timezone.localdate()
        template = _make_template()
        _make_node(template, today - timedelta(days=400))
        _make_node(template, today)

        payload = _review(authenticated_client, **_window(today))

        assert _task(payload, template)["late_outside_period"] is True

    def test_late_after_a_past_period(self, authenticated_client):
        today = timezone.localdate()
        template = _make_template()
        shown = today - timedelta(days=400)
        _make_node(template, shown, status="completed")
        _make_node(template, today - timedelta(days=40))

        payload = _review(authenticated_client, **_window(shown))

        assert _task(payload, template)["late_outside_period"] is True

    def test_closed_occurrences_are_not_late(self, authenticated_client):
        today = timezone.localdate()
        template = _make_template()
        _make_node(template, today - timedelta(days=380), status="completed")
        _make_node(template, today - timedelta(days=390), status="cancelled")
        _make_node(template, today)

        payload = _review(authenticated_client, **_window(today))

        assert _task(payload, template)["late_outside_period"] is False

    def test_a_range_in_the_future_does_not_make_upcoming_work_late(
        self, authenticated_client
    ):
        today = timezone.localdate()
        template = _make_template()
        _make_node(template, today + timedelta(days=10))
        shown = today + timedelta(days=200)
        _make_node(template, shown)

        payload = _review(authenticated_client, **_window(shown))

        assert _task(payload, template)["late_outside_period"] is False

    def test_overdue_filter_keeps_a_task_late_only_before_the_period(
        self, authenticated_client
    ):
        today = timezone.localdate()
        late_before = _make_template(name="Late before the period")
        _make_node(late_before, today - timedelta(days=400))
        on_time = _make_template(name="On time")
        _make_node(on_time, today + timedelta(days=1))

        payload = _review(
            authenticated_client,
            **_window(today, today + timedelta(days=1)),
            status="overdue",
        )
        names = [task["name"] for f in payload["folders"] for task in f["tasks"]]

        assert names == ["Late before the period"]


@pytest.mark.django_db
class TestFilters:
    def _ids(self, payload):
        return {task["id"] for folder in payload["folders"] for task in folder["tasks"]}

    def test_several_statuses(self, authenticated_client):
        today = timezone.localdate()
        late, upcoming = today - timedelta(days=40), today + timedelta(days=40)
        window = _window(late, upcoming)
        overdue = _make_template(name="Overdue task")
        _make_node(overdue, late, status="pending")
        done = _make_template(name="Done task")
        _make_node(done, late, status="completed")
        cancelled = _make_template(name="Cancelled task")
        _make_node(cancelled, late, status="cancelled")

        def ids(*statuses):
            params = {**window, "status": list(statuses)}
            return self._ids(_review(authenticated_client, **params))

        assert ids("overdue", "completed") == {str(overdue.id), str(done.id)}
        assert ids("cancelled") == {str(cancelled.id)}
        # An overdue occurrence is still pending.
        assert ids("pending") == {str(overdue.id)}
        assert ids() == {str(overdue.id), str(done.id), str(cancelled.id)}

    def test_folder_is_exact_unless_subfolders_are_asked_for(
        self, authenticated_client
    ):
        root = Folder.get_root_folder()
        parent = Folder.objects.create(name="Plant", parent_folder=root)
        child = Folder.objects.create(name="Line 1", parent_folder=parent)
        grandchild = Folder.objects.create(name="Cell A", parent_folder=child)
        today = timezone.localdate()

        def template(name, folder):
            tpl = TaskTemplate.objects.create(
                name=name,
                folder=folder,
                is_recurrent=True,
                task_date=date(2020, 1, 1),
                schedule={"interval": 1, "frequency": "MONTHLY"},
            )
            _make_node(tpl, today)
            return str(tpl.id)

        at_root = template("Root task", root)
        at_parent = template("Plant task", parent)
        at_child = template("Line task", child)
        at_grandchild = template("Cell task", grandchild)

        def ids(folder, **extra):
            params = {**_window(today), "folder": str(folder.id), **extra}
            return self._ids(_review(authenticated_client, **params))

        assert ids(parent) == {at_parent}
        assert ids(parent, include_subfolders="true") == {
            at_parent,
            at_child,
            at_grandchild,
        }
        assert ids(child, include_subfolders="true") == {at_child, at_grandchild}
        assert at_root not in ids(parent, include_subfolders="true")


@pytest.mark.django_db
class TestAppliedControlsOfADomainPlan:
    """applied-controls?recurrent_task_folder=<domain>: the controls its plan covers."""

    URL = "/api/applied-controls/"

    def _names(self, client, folder, **extra):
        params = {"recurrent_task_folder": str(folder.id), **extra}
        response = client.get(self.URL, params)
        assert response.status_code == 200
        return sorted(row["name"] for row in response.json()["results"])

    def test_lists_controls_linked_to_the_domain_recurrent_tasks(
        self, authenticated_client
    ):
        root = Folder.get_root_folder()
        domain = Folder.objects.create(name="Plant", parent_folder=root)
        other = Folder.objects.create(name="Office", parent_folder=root)

        local = AppliedControl.objects.create(name="Local control", folder=domain)
        # Lives elsewhere, but a task of the domain is linked to it.
        remote = AppliedControl.objects.create(name="Remote control", folder=other)
        # In the domain, yet no recurrent task covers it.
        AppliedControl.objects.create(name="Uncovered control", folder=domain)
        one_off = AppliedControl.objects.create(name="One-off control", folder=domain)
        disabled = AppliedControl.objects.create(name="Disabled control", folder=domain)
        elsewhere = AppliedControl.objects.create(name="Office control", folder=other)

        def task(name, folder, controls, **fields):
            template = TaskTemplate.objects.create(
                name=name,
                folder=folder,
                task_date=date(2020, 1, 1),
                **{
                    "is_recurrent": True,
                    "schedule": {"interval": 1, "frequency": "MONTHLY"},
                    **fields,
                },
            )
            template.applied_controls.set(controls)
            return template

        task("Monthly check", domain, [local, remote])
        task("Second check", domain, [local])
        task("One-off", domain, [one_off], is_recurrent=False, schedule=None)
        task("Paused", domain, [disabled], enabled=False)
        task("Office check", other, [elsewhere])
        # Sub-domains count only when asked for.
        line = Folder.objects.create(name="Line 1", parent_folder=domain)
        nested = AppliedControl.objects.create(name="Line control", folder=line)
        task("Line check", line, [nested])

        assert self._names(authenticated_client, domain) == [
            "Local control",
            "Remote control",
        ]
        assert self._names(authenticated_client, domain, include_subfolders="true") == [
            "Line control",
            "Local control",
            "Remote control",
        ]
        assert self._names(authenticated_client, line) == ["Line control"]
        assert self._names(authenticated_client, other) == ["Office control"]

    def test_hidden_domain_is_refused_like_an_unknown_one(self):
        root = Folder.get_root_folder()
        seen = Folder.objects.create(name="Seen", parent_folder=root)
        hidden = Folder.objects.create(name="Hidden", parent_folder=root)
        user = User.objects.create_user(f"plan-{uuid.uuid4().hex[:6]}@test.com")
        RoleAssignment.objects.create(
            user=user,
            role=Role.objects.get(name=RoleCodename.ANALYST.value),
            folder=root,
            is_recursive=True,
        ).perimeter_folders.add(seen)
        client = APIClient()
        _, token = AuthToken.objects.create(user=user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        def status_for(folder_id):
            return client.get(
                self.URL, {"recurrent_task_folder": folder_id}
            ).status_code

        assert status_for(str(seen.id)) == 200
        assert status_for(str(hidden.id)) == 400
        assert status_for(str(uuid.uuid4())) == 400


@pytest.mark.django_db
class TestOccurrenceWindow:
    """The occurrence page reads the neighbours of an occurrence from the list."""

    def _ids(self, client, template, lookup, day, ordering):
        response = client.get(
            "/api/task-nodes/",
            {
                "task_template": str(template.id),
                lookup: day.isoformat(),
                "ordering": ordering,
                "limit": 2,
            },
        )
        assert response.status_code == 200
        return [node["id"] for node in response.json()["results"]]

    def test_nearest_occurrences_come_first_on_each_side(self, authenticated_client):
        template = _make_template()
        nodes = [_make_node(template, date(2026, month, 10)) for month in range(1, 7)]
        # Another task's occurrence in between is not a neighbour.
        _make_node(_make_template(name="Other task"), date(2026, 3, 20))
        viewed = nodes[3]

        before = self._ids(
            authenticated_client, template, "due_date__lt", viewed.due_date, "-due_date"
        )
        after = self._ids(
            authenticated_client, template, "due_date__gt", viewed.due_date, "due_date"
        )

        assert before == [str(nodes[2].id), str(nodes[1].id)]
        assert after == [str(nodes[4].id), str(nodes[5].id)]
