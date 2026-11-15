import pytest
from rest_framework.test import APIClient

from core.models import Incident, TimelineEntry
from iam.models import Folder, User


@pytest.fixture
def setup(db):
    domain = Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="Incidents Domain",
        content_type=Folder.ContentType.DOMAIN,
    )
    client = APIClient()
    client.force_authenticate(User.objects.create_superuser("incidents@tests.com"))
    return domain, client


def test_patch_incident_logs_status_and_severity_timeline(setup):
    domain, client = setup
    incident = Incident.objects.create(
        name="Incident", folder=domain, severity=Incident.Severity.SEV1
    )

    res = client.patch(
        f"/api/incidents/{incident.id}/",
        {"status": Incident.Status.ONGOING, "severity": Incident.Severity.SEV2},
        format="json",
    )

    assert res.status_code == 200, res.json()
    entries = set(
        TimelineEntry.objects.filter(incident=incident).values_list(
            "entry_type", "entry"
        )
    )
    assert (TimelineEntry.EntryType.STATUS_CHANGED, "New->Ongoing") in entries
    assert (TimelineEntry.EntryType.SEVERITY_CHANGED, "Critical->Major") in entries


def test_batch_change_incident_status_logs_timeline(setup):
    domain, client = setup
    incidents = [
        Incident.objects.create(name=f"Incident {i}", folder=domain) for i in range(3)
    ]

    res = client.post(
        "/api/incidents/batch-action/",
        {
            "action": "change_field",
            "ids": [str(i.id) for i in incidents],
            "field": "status",
            "value": Incident.Status.CLOSED,
        },
        format="json",
    )

    assert res.status_code == 200, res.json()
    assert res.json()["failed"] == []
    for incident in incidents:
        incident.refresh_from_db()
        assert incident.status == Incident.Status.CLOSED
        assert TimelineEntry.objects.filter(
            incident=incident,
            entry_type=TimelineEntry.EntryType.STATUS_CHANGED,
            entry="New->Closed",
        ).exists()
