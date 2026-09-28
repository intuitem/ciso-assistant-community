"""
Producer wiring. The invariant under test is that consolidating the three sweeps
changed *nothing* about email, while giving the inbox a condition that persists for
as long as it is true.

Sweeps are invoked with `.call_local()`: HUEY runs with `immediate: False`, so calling
a @db_periodic_task normally just enqueues it for a consumer that is not running here.
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from core.models import Evidence
from iam.models import Folder, User
from notifications.models import Notification

pytestmark = pytest.mark.django_db


@pytest.fixture
def folder(db):
    return Folder.objects.create(
        name="Producer test domain", content_type=Folder.ContentType.DOMAIN
    )


@pytest.fixture
def owner(db):
    return User.objects.create(email="owner@test.local")


def _evidence(folder, owner, days_out, name="Backup log"):
    ev = Evidence.objects.create(
        name=name, folder=folder, expiry_date=date.today() + timedelta(days=days_out)
    )
    # Evidence.owner is M2M to core.Actor; ActorSyncMixin.save() creates one per User.
    ev.owner.set([owner.actor])
    return ev


def _rows():
    return Notification.objects.filter(type="evidence_expiring_soon")


@pytest.mark.parametrize("days_out", [30, 7, 1])
def test_email_still_fires_on_exactly_the_same_days(folder, owner, days_out):
    from core.tasks import check_evidences_expiring_soon

    _evidence(folder, owner, days_out)
    with patch("core.tasks.send_evidence_expiring_soon_notification") as send:
        check_evidences_expiring_soon.call_local()
    assert send.call_count == 1
    assert send.call_args.kwargs["days"] == days_out


@pytest.mark.parametrize("days_out", [29, 12, 2])
def test_email_does_not_fire_between_the_escalation_days(folder, owner, days_out):
    from core.tasks import check_evidences_expiring_soon

    _evidence(folder, owner, days_out)
    with patch("core.tasks.send_evidence_expiring_soon_notification") as send:
        check_evidences_expiring_soon.call_local()
    assert send.call_count == 0


@pytest.mark.parametrize("days_out", [30, 29, 12, 7, 2, 1])
def test_the_inbox_row_persists_across_the_whole_window(folder, owner, days_out):
    """The reason the three tasks had to become one: an exact-day sweep would have
    deleted this row on every day that is not 30, 7 or 1."""
    from core.tasks import check_evidences_expiring_soon

    ev = _evidence(folder, owner, days_out)
    with patch("core.tasks.send_evidence_expiring_soon_notification"):
        check_evidences_expiring_soon.call_local()
    row = _rows().get()
    assert row.object_id == ev.id
    assert row.context["days_remaining"] == str(days_out)


def test_the_row_clears_when_the_condition_stops_being_true(folder, owner):
    from core.tasks import check_evidences_expiring_soon

    ev = _evidence(folder, owner, 10)
    with patch("core.tasks.send_evidence_expiring_soon_notification"):
        check_evidences_expiring_soon.call_local()
    assert _rows().count() == 1

    ev.expiry_date = date.today() + timedelta(days=365)
    ev.save()
    with patch("core.tasks.send_evidence_expiring_soon_notification"):
        check_evidences_expiring_soon.call_local()
    assert _rows().count() == 0, "pushed out of the window, so it no longer applies"


def test_a_read_row_is_not_reopened_by_the_next_nightly_run(folder, owner):
    from core.tasks import check_evidences_expiring_soon

    _evidence(folder, owner, 10)
    with patch("core.tasks.send_evidence_expiring_soon_notification"):
        check_evidences_expiring_soon.call_local()
    _rows().update(is_read=True)

    with patch("core.tasks.send_evidence_expiring_soon_notification"):
        check_evidences_expiring_soon.call_local()
    assert _rows().get().is_read is True


def test_one_row_per_object_not_one_per_sweep(folder, owner):
    from core.tasks import check_evidences_expiring_soon

    _evidence(folder, owner, 10)
    for _ in range(5):
        with patch("core.tasks.send_evidence_expiring_soon_notification"):
            check_evidences_expiring_soon.call_local()
    assert _rows().count() == 1, "five nights, one row -- the whole point of the upsert"


# --- the consolidated deadline sweeps -------------------------------------------------
# Each replaced an in_month / in_week / tomorrow trio. The invariant is the same for all:
# email fires on exactly the old days, the inbox tracks the whole window.


@pytest.fixture
def control(folder):
    from core.models import AppliedControl

    return AppliedControl.objects.create(name="Encrypt backups", folder=folder)


def _assign(obj, owner, field="owner"):
    getattr(obj, field).set([owner.actor])
    return obj


@pytest.mark.parametrize(
    "days_out,fires",
    [(30, True), (7, True), (1, True), (29, False), (12, False), (2, False)],
)
def test_control_expiry_email_fires_only_on_the_old_days(
    folder, owner, control, days_out, fires
):
    from core.tasks import check_applied_controls_expiring_soon

    control.expiry_date = date.today() + timedelta(days=days_out)
    control.save()
    _assign(control, owner)
    with patch("core.tasks.send_applied_control_expiring_soon_notification") as send:
        check_applied_controls_expiring_soon.call_local()
    assert (send.call_count == 1) is fires
    if fires:
        assert send.call_args.kwargs["days"] == days_out


@pytest.mark.parametrize("days_out", [30, 29, 12, 7, 2, 1])
def test_control_expiry_row_persists_across_the_window(
    folder, owner, control, days_out
):
    from core.tasks import check_applied_controls_expiring_soon

    control.expiry_date = date.today() + timedelta(days=days_out)
    control.save()
    _assign(control, owner)
    with patch("core.tasks.send_applied_control_expiring_soon_notification"):
        check_applied_controls_expiring_soon.call_local()
    row = Notification.objects.get(type="applied_control_expiring_soon")
    assert row.context["days_remaining"] == str(days_out)


def test_control_expiry_row_clears_when_pushed_out_of_the_window(
    folder, owner, control
):
    from core.tasks import check_applied_controls_expiring_soon

    control.expiry_date = date.today() + timedelta(days=10)
    control.save()
    _assign(control, owner)
    with patch("core.tasks.send_applied_control_expiring_soon_notification"):
        check_applied_controls_expiring_soon.call_local()
    assert (
        Notification.objects.filter(type="applied_control_expiring_soon").count() == 1
    )

    control.expiry_date = date.today() + timedelta(days=365)
    control.save()
    with patch("core.tasks.send_applied_control_expiring_soon_notification"):
        check_applied_controls_expiring_soon.call_local()
    assert (
        Notification.objects.filter(type="applied_control_expiring_soon").count() == 0
    )


def test_expired_controls_single_sweep_writes_and_clears(folder, owner, control):
    from core.tasks import check_controls_with_expired_eta

    control.eta = date.today() - timedelta(days=3)
    control.status = "to_do"
    control.save()
    _assign(control, owner)
    with patch("core.tasks.send_notification_email_expired_eta"):
        check_controls_with_expired_eta.call_local()
    assert Notification.objects.filter(type="expired_controls").count() == 1

    control.status = "active"
    control.save()
    with patch("core.tasks.send_notification_email_expired_eta"):
        check_controls_with_expired_eta.call_local()
    assert Notification.objects.filter(type="expired_controls").count() == 0, (
        "marking the control active is what the reminder said would stop it"
    )


def _sweep():
    from core.tasks import check_evidences_expiring_soon

    with patch("core.tasks.send_evidence_expiring_soon_notification"):
        check_evidences_expiring_soon.call_local()


def _move_to(ev, days_out):
    ev.expiry_date = date.today() + timedelta(days=days_out)
    ev.save()


@pytest.mark.parametrize("days_out", [7, 1])
def test_a_read_row_reopens_when_the_deadline_escalates(folder, owner, days_out):
    """Reading "expires in 30 days" must not silence "expires in 1 day". The inbox
    escalates on exactly the days email does."""
    ev = _evidence(folder, owner, 30)
    _sweep()
    _rows().update(is_read=True, read_at=date.today())

    _move_to(ev, days_out)
    _sweep()

    row = _rows().get()
    assert row.is_read is False
    assert row.read_at is None
    assert row.context["days_remaining"] == str(days_out)


@pytest.mark.parametrize("days_out", [29, 10, 2])
def test_a_read_row_stays_read_on_a_non_escalation_day(folder, owner, days_out):
    """The other side of it: the sweep runs nightly, so re-opening on any day the
    condition merely still holds would nag daily."""
    ev = _evidence(folder, owner, 30)
    _sweep()
    _rows().update(is_read=True)

    _move_to(ev, days_out)
    _sweep()

    assert _rows().get().is_read is True


def test_escalation_still_writes_exactly_one_row(folder, owner):
    """The sweep now calls notify_many twice; the natural key must still collapse."""
    ev = _evidence(folder, owner, 30)
    _sweep()
    _move_to(ev, 7)
    _sweep()
    assert _rows().count() == 1


# --- assignment notifications: one row per audit, not per assignment ------------------


@pytest.fixture
def audit(folder):
    from core.models import ComplianceAssessment, Framework, Perimeter

    framework = Framework.objects.create(
        name="FW", folder=folder, urn="urn:test:fw:assignments"
    )
    perimeter = Perimeter.objects.create(name="P", folder=folder)
    return ComplianceAssessment.objects.create(
        name="ISO audit", framework=framework, folder=folder, perimeter=perimeter
    )


def _assignment(audit, folder, actor_user):
    from core.models import RequirementAssignment

    assignment = RequirementAssignment.objects.create(
        compliance_assessment=audit, folder=folder
    )
    assignment.actor.set([actor_user.actor])
    return assignment


def test_two_assignments_in_one_audit_share_one_row(audit, folder, owner):
    """Deliberate (§12.5): the target is the audit, which is both the dedup key and the
    click destination. The declared context is audit-level, so per-assignment rows would
    be identical duplicates."""
    from core.tasks import send_assignment_activated_notification

    first = _assignment(audit, folder, owner)
    second = _assignment(audit, folder, owner)

    send_assignment_activated_notification.call_local(first.id)
    send_assignment_activated_notification.call_local(second.id)

    rows = Notification.objects.filter(type="assignment_activated", recipient=owner)
    assert rows.count() == 1
    assert rows.get().object_id == audit.id


def test_the_newest_review_decision_is_the_one_on_the_row(audit, folder, owner):
    """The cost of sharing a row: `decision` is per-assignment, so the second review
    overwrites the first. Accepted -- the row re-opens unread, so the user sees the
    latest and opens the audit for the rest."""
    from core.tasks import send_assignment_reviewed_notification

    first = _assignment(audit, folder, owner)
    second = _assignment(audit, folder, owner)

    send_assignment_reviewed_notification.call_local(first.id, "changes_requested")
    Notification.objects.filter(type="assignment_reviewed").update(is_read=True)
    send_assignment_reviewed_notification.call_local(second.id, "closed")

    row = Notification.objects.get(type="assignment_reviewed", recipient=owner)
    assert row.context["decision"] == "Closed"
    assert row.is_read is False, "a new decision re-opens the row"
