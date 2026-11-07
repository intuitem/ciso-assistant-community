"""Regulatory reminders: NIS2 / GDPR 72h deadlines, data subject requests, contracts,
and gaps in the record of processing activities.

Sweeps run with `.call_local()`: HUEY is not immediate in tests.
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from core.models import Incident, Terminology
from core.tasks import (
    check_contracts_expiring_soon,
    check_processing_obligations,
    check_regulatory_deadlines,
    check_right_requests_due_soon,
    processing_obligation_gaps,
)
from iam.models import Folder, User
from notifications.models import Notification
from privacy.models import DataBreach, PersonalData, Processing, Purpose, RightRequest
from privacy.test_data_breach import admin_client, domain  # noqa: F401
from tprm.models import Contract

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def nis2_flag():
    with patch("core.tasks.ff_is_enabled", return_value=True) as flag:
        yield flag


@pytest.fixture
def folder():
    return Folder.objects.create(
        name="Regulatory alerts", content_type=Folder.ContentType.DOMAIN
    )


@pytest.fixture
def owner():
    return User.objects.create(email="dpo@test.local")


def _rows(kind):
    return Notification.objects.filter(type=kind)


def test_nis2_stage_alerts_owner_and_escalates_on_the_hour(folder, owner):
    incident = Incident.objects.create(
        name="Ransomware",
        folder=folder,
        nis2_significant=True,
        # early warning due in 6h30: the 6h bucket
        reported_at=timezone.now() - timedelta(hours=17, minutes=30),
    )
    incident.owners.set([owner.actor])
    with patch("core.tasks.send_regulatory_deadline_notification") as send:
        check_regulatory_deadlines.call_local()
    (row,) = _rows("regulatory_deadline")
    assert row.context["deadline_key"] == "earlyWarning"  # label key, not the stage id
    send.assert_called_once()
    assert send.call_args.args[0] == "dpo@test.local"

    # once sent, the next stage takes over the same row
    incident.nis2_early_warning_at = timezone.now()
    incident.save()
    with patch("core.tasks.send_regulatory_deadline_notification") as send:
        check_regulatory_deadlines.call_local()
    (row,) = _rows("regulatory_deadline")
    assert row.context["deadline_key"] == "incidentNotification"
    send.assert_not_called()  # 54h left: no escalation bucket


def test_nis2_alerts_need_the_nis2_flag(folder, owner, nis2_flag):
    nis2_flag.return_value = False
    incident = Incident.objects.create(
        name="Botnet",
        folder=folder,
        nis2_significant=True,
        reported_at=timezone.now() - timedelta(hours=2),
    )
    incident.owners.set([owner.actor])
    check_regulatory_deadlines.call_local()
    assert _rows("regulatory_deadline").count() == 0


def test_missed_early_warning_does_not_hide_the_72h_notification(folder, owner):
    incident = Incident.objects.create(
        name="Wiper",
        folder=folder,
        nis2_significant=True,
        reported_at=timezone.now() - timedelta(hours=30),  # 24h missed, 72h ahead
    )
    incident.owners.set([owner.actor])
    check_regulatory_deadlines.call_local()
    (row,) = _rows("regulatory_deadline")
    assert row.context["deadline_key"] == "incidentNotification"


def _emailed_keys(send) -> list[str]:
    return [d["deadline_key"] for d in send.call_args.args[1]]


def test_missed_early_warning_still_gets_its_just_missed_email(folder, owner):
    incident = Incident.objects.create(
        name="Wiper",
        folder=folder,
        nis2_significant=True,
        reported_at=timezone.now() - timedelta(hours=24, minutes=30),
    )
    incident.owners.set([owner.actor])
    with patch("core.tasks.send_regulatory_deadline_notification") as send:
        check_regulatory_deadlines.call_local()
    # the inbox row has moved on to the 72h notification, the email has not
    (row,) = _rows("regulatory_deadline")
    assert row.context["deadline_key"] == "incidentNotification"
    send.assert_called_once()
    assert _emailed_keys(send) == ["earlyWarning"]

    # one email per missed stage: an hour later there is nothing new to say
    incident.reported_at -= timedelta(hours=1)
    incident.save()
    with patch("core.tasks.send_regulatory_deadline_notification") as send:
        check_regulatory_deadlines.call_local()
    send.assert_not_called()


def test_final_report_warns_while_the_72h_notification_is_overdue(folder, owner):
    # 72h notification never sent: the inbox row stays on it. Fixed clock, since
    # "one month" depends on the date: 72h due 10 Feb 18:30, final report 10 Mar 18:30
    current = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)  # final report 6h30 away
    reported_at = datetime(2026, 2, 7, 18, 30, tzinfo=UTC)
    incident = Incident.objects.create(
        name="Supply chain",
        folder=folder,
        nis2_significant=True,
        reported_at=reported_at,
        nis2_early_warning_at=reported_at + timedelta(hours=6),
    )
    incident.owners.set([owner.actor])
    with (
        patch("core.models.now", return_value=current),
        patch("core.tasks.now", return_value=current),
        patch("core.tasks.send_regulatory_deadline_notification") as send,
    ):
        check_regulatory_deadlines.call_local()
    (row,) = _rows("regulatory_deadline")
    assert row.context["deadline_key"] == "incidentNotification"
    send.assert_called_once()
    assert _emailed_keys(send) == ["finalReport"]


def test_breach_in_notified_status_without_date_is_not_alerted(folder, owner):
    breach = DataBreach.objects.create(
        name="Misdirected email",
        folder=folder,
        discovered_on=timezone.now() - timedelta(hours=80),
        status="privacy_authority_notified",
    )
    breach.assigned_to.set([owner.actor])
    check_regulatory_deadlines.call_local()
    assert _rows("regulatory_deadline").count() == 0
    assert breach.authority_notification_overdue is False


def test_breach_alert_clears_once_notified(folder, owner):
    breach = DataBreach.objects.create(
        name="Lost laptop",
        folder=folder,
        discovered_on=timezone.now() - timedelta(hours=10),
    )
    breach.assigned_to.set([owner.actor])
    check_regulatory_deadlines.call_local()
    assert _rows("regulatory_deadline").count() == 1

    breach.authority_notified_on = timezone.now()
    breach.save()
    check_regulatory_deadlines.call_local()
    assert _rows("regulatory_deadline").count() == 0


def test_right_request_due_soon(folder, owner):
    request = RightRequest.objects.create(
        name="Access request",
        folder=folder,
        requested_on=date.today() - timedelta(days=23),
        due_date=date.today() + timedelta(days=7),
    )
    request.owner.set([owner.actor])
    with patch("core.tasks.send_right_request_due_soon_notification") as send:
        check_right_requests_due_soon.call_local()
    assert _rows("right_request_due_soon").count() == 1
    send.assert_called_once()
    assert send.call_args.args[:2] == ("dpo@test.local", ["Access request"])


def test_right_request_defaults_to_one_month(admin_client, domain):  # noqa: F811
    res = admin_client.post(
        "/api/privacy/right-requests/",
        {"name": "Erasure", "folder": str(domain.id), "requested_on": "2026-01-31"},
        format="json",
    )
    assert res.status_code == 201, res.json()
    assert res.json()["due_date"] == "2026-02-28"


def test_contract_expiring_soon(folder, owner):
    contract = Contract.objects.create(
        name="Hosting",
        folder=folder,
        status=Contract.Status.ACTIVE,
        end_date=date.today() + timedelta(days=30),
    )
    contract.owner.set([owner.actor])
    with patch("core.tasks.send_contract_expiring_soon_notification") as send:
        check_contracts_expiring_soon.call_local()
    assert _rows("contract_expiring_soon").count() == 1
    send.assert_called_once()


def test_processing_gaps(folder, owner):
    processing = Processing.objects.create(name="Payroll", folder=folder)
    processing.assigned_to.set([owner.actor])
    assert processing_obligation_gaps(processing) == ["gapNoPurpose"]

    Purpose.objects.create(name="Pay salaries", processing=processing, folder=folder)
    category = Terminology.objects.filter(
        field_path=Terminology.FieldPath.PERSONAL_DATA_CATEGORY
    ).first() or Terminology.objects.create(
        name="identity",
        field_path=Terminology.FieldPath.PERSONAL_DATA_CATEGORY,
        is_visible=True,
    )
    PersonalData.objects.create(
        name="Bank account",
        processing=processing,
        folder=folder,
        category=category,
    )
    processing.dpia_required = True
    processing.save()
    assert processing_obligation_gaps(processing) == [
        "gapDpiaMissing",
        "gapRetentionMissing",
    ]

    check_processing_obligations.call_local()
    (row,) = _rows("processing_obligation_gap")
    assert str(row.context["gap_count"]) == "2"


def test_dpia_recorded_as_a_reference_is_not_a_gap(folder, owner):
    """A DPIA run outside the app is recorded in dpia_reference; the dpia link is
    read-only, so it could never clear the gap."""
    processing = Processing.objects.create(
        name="Recruitment",
        folder=folder,
        dpia_required=True,
        dpia_reference="DPIA-2025-02",
    )
    processing.assigned_to.set([owner.actor])
    Purpose.objects.create(name="Hire staff", processing=processing, folder=folder)
    assert processing_obligation_gaps(processing) == []

    check_processing_obligations.call_local()
    assert _rows("processing_obligation_gap").count() == 0
