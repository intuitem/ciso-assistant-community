"""Tasks through the mapped import: a team's security calendar becomes task
definitions with their schedule, assignees and the controls they maintain."""

import io
import json
from datetime import date
from pathlib import Path

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import AppliedControl, TaskNode, TaskTemplate
from iam.models import User

SAMPLES = Path(__file__).parent / "samples"
IMPORT_URL = "/api/data-wizard/mapping/import/"
CALENDAR = "12_security_calendar.xlsx"
STEP = {
    "model_type": "TaskTemplate",
    "sheets": [
        {
            "source": "Calendar",
            "target": "Summary",
            "header_row": 3,
            "columns": {
                "Ref": "ref_id",
                "Activity": "name",
                "What to do": "description",
                "Recurring": "is_recurrent",
                "Start": "task_date",
                "Frequency": "schedule_frequency",
                "Every": "schedule_interval",
                "Owner": "assigned_to",
                "Control maintained": "applied_controls",
            },
        }
    ],
}


def _import(client, folder, dry_run=False):
    return client.post(
        IMPORT_URL,
        {
            "file": SimpleUploadedFile(CALENDAR, (SAMPLES / CALENDAR).read_bytes()),
            "mapping": json.dumps({"steps": [STEP]}),
            "options": json.dumps({"folder_id": str(folder.id), "on_conflict": "skip"}),
            "dry_run": str(dry_run).lower(),
        },
        format="multipart",
    )


@pytest.mark.django_db
class TestCalendar:
    def test_rows_become_scheduled_tasks(
        self, api_client, domain_folder, all_accessible
    ):
        User.objects.create_user("it-ops@acme.com")
        control = AppliedControl.objects.create(
            name="Quarterly access review", folder=domain_folder
        )
        resp = _import(api_client, domain_folder)
        assert resp.status_code == 200, resp.json()
        review = TaskTemplate.objects.get(ref_id="CAL-01")
        assert review.is_recurrent
        assert review.schedule["frequency"] == "MONTHLY"
        assert review.schedule["interval"] == 3
        assert list(review.applied_controls.all()) == [control]
        assert [a.user.email for a in review.assigned_to.all()] == ["it-ops@acme.com"]
        assert not TaskTemplate.objects.get(ref_id="CAL-05").is_recurrent

    def test_frequency_without_interval_is_refused(
        self, api_client, domain_folder, all_accessible
    ):
        resp = _import(api_client, domain_folder)
        errors = json.dumps(resp.json()["steps"][0]["results"])
        assert "schedule_interval must be provided together" in errors
        assert not TaskTemplate.objects.filter(ref_id="CAL-04").exists()

    def test_dry_run_creates_nothing(self, api_client, domain_folder, all_accessible):
        resp = _import(api_client, domain_folder, dry_run=True)
        assert resp.status_code == 200
        assert not TaskTemplate.objects.exists()

    def test_a_period_without_frequency_counts_days(
        self, api_client, domain_folder, all_accessible
    ):
        columns = {
            k: v
            for k, v in STEP["sheets"][0]["columns"].items()
            if k not in ("Frequency", "Recurring", "Control maintained")
        }
        defaults = {"schedule_frequency": "DAILY", "is_recurrent": True}
        sheet = {**STEP["sheets"][0], "columns": columns, "defaults": defaults}
        resp = api_client.post(
            IMPORT_URL,
            {
                "file": SimpleUploadedFile(CALENDAR, (SAMPLES / CALENDAR).read_bytes()),
                "mapping": json.dumps({"steps": [{**STEP, "sheets": [sheet]}]}),
                "options": json.dumps(
                    {"folder_id": str(domain_folder.id), "on_conflict": "skip"}
                ),
            },
            format="multipart",
        )
        assert resp.status_code == 200, resp.json()
        review = TaskTemplate.objects.get(ref_id="CAL-01")
        assert review.is_recurrent
        assert (review.schedule["frequency"], review.schedule["interval"]) == (
            "DAILY",
            3,
        )
        # A row without a period stays a one-off task.
        assert not TaskTemplate.objects.get(ref_id="CAL-05").schedule

    def test_a_frequency_without_period_counts_one(
        self, api_client, domain_folder, all_accessible
    ):
        columns = {
            k: v for k, v in STEP["sheets"][0]["columns"].items() if k != "Every"
        }
        sheet = {
            **STEP["sheets"][0],
            "columns": columns,
            "defaults": {"schedule_interval": 1},
        }
        resp = api_client.post(
            IMPORT_URL,
            {
                "file": SimpleUploadedFile(CALENDAR, (SAMPLES / CALENDAR).read_bytes()),
                "mapping": json.dumps({"steps": [{**STEP, "sheets": [sheet]}]}),
                "options": json.dumps(
                    {"folder_id": str(domain_folder.id), "on_conflict": "skip"}
                ),
            },
            format="multipart",
        )
        assert resp.status_code == 200, resp.json()
        phishing = TaskTemplate.objects.get(ref_id="CAL-04")
        assert (phishing.schedule["frequency"], phishing.schedule["interval"]) == (
            "WEEKLY",
            1,
        )
        assert not TaskTemplate.objects.get(ref_id="CAL-05").schedule

    def test_default_cannot_override_a_mapped_column(
        self, api_client, domain_folder, all_accessible
    ):
        sheet = {**STEP["sheets"][0], "defaults": {"name": "Same for all"}}
        resp = api_client.post(
            IMPORT_URL,
            {
                "file": SimpleUploadedFile(CALENDAR, (SAMPLES / CALENDAR).read_bytes()),
                "mapping": json.dumps({"steps": [{**STEP, "sheets": [sheet]}]}),
                "options": json.dumps({"folder_id": str(domain_folder.id)}),
            },
            format="multipart",
        )
        assert resp.status_code == 400
        assert not TaskTemplate.objects.exists()


def _periodic_controls():
    """The shape of a periodic-control list: a period in days, the last check
    and the next one (last + period)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Contrôles"
    ws.append(["Réf", "Titre", "Périodicité", "Dernier contrôle", "Prochain contrôle"])
    ws.append(["123", "Check iOS updates", 60, date(2026, 4, 21), date(2026, 6, 20)])
    ws.append(["34", "Check network ACLs", 180, date(2026, 8, 13), date(2027, 2, 9)])
    ws.append(["7", "Review firewall rules", 365, None, date(2026, 11, 24)])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


@pytest.mark.django_db
class TestLastAndNextDates:
    def _import(self, client, folder, columns):
        sheet = {
            "source": "Contrôles",
            "target": "Summary",
            "columns": {
                "Réf": "ref_id",
                "Titre": "name",
                "Périodicité": "schedule_interval",
                **columns,
            },
            "defaults": {"schedule_frequency": "DAILY", "is_recurrent": True},
        }
        return client.post(
            IMPORT_URL,
            {
                "file": SimpleUploadedFile("controles.xlsx", _periodic_controls()),
                "mapping": json.dumps(
                    {"steps": [{"model_type": "TaskTemplate", "sheets": [sheet]}]}
                ),
                "options": json.dumps(
                    {"folder_id": str(folder.id), "on_conflict": "skip"}
                ),
            },
            format="multipart",
        )

    def test_last_done_is_a_completed_occurrence_and_the_start(
        self, api_client, domain_folder, all_accessible
    ):
        resp = self._import(
            api_client,
            domain_folder,
            {"Dernier contrôle": "last_done", "Prochain contrôle": "next_occurrence"},
        )
        assert resp.status_code == 200, resp.json()
        ios = TaskTemplate.objects.get(ref_id="123")
        assert ios.task_date == date(2026, 4, 21)
        done = TaskNode.objects.get(task_template=ios, due_date=date(2026, 4, 21))
        assert done.status == "completed"
        # No last check: the schedule starts at the next one.
        firewall = TaskTemplate.objects.get(ref_id="7")
        assert firewall.task_date == date(2026, 11, 24)
        assert not TaskNode.objects.filter(
            task_template=firewall, status="completed"
        ).exists()

    def test_dry_run_counts_the_occurrences(
        self, api_client, domain_folder, all_accessible
    ):
        resp = api_client.post(
            IMPORT_URL,
            {
                "file": SimpleUploadedFile("controles.xlsx", _periodic_controls()),
                "mapping": json.dumps(
                    {
                        "steps": [
                            {
                                "model_type": "TaskTemplate",
                                "sheets": [
                                    {
                                        "source": "Contrôles",
                                        "target": "Summary",
                                        "columns": {
                                            "Titre": "name",
                                            "Dernier contrôle": "last_done",
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                ),
                "options": json.dumps({"folder_id": str(domain_folder.id)}),
                "dry_run": "true",
            },
            format="multipart",
        )
        results = resp.json()["steps"][0]["results"]
        assert results["task_nodes"]["failed"] == 0, results
        assert not TaskTemplate.objects.exists()
