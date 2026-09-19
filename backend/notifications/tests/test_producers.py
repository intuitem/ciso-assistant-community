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
    assert f"{days_out} day" in row.title


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
