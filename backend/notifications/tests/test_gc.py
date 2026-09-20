"""
Garbage collection. Three mechanisms, each with a different job:
clear_stale removes conditions that stopped being true, retention removes read rows
that have aged out, and the cap is a ceiling on one inbox regardless of state.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from core.models import AppliedControl
from iam.models import Folder, User
from notifications.models import Notification
from notifications.tasks import (
    MAX_PER_RECIPIENT,
    RETENTION_DAYS,
    enforce_per_recipient_cap,
    prune_orphaned_notifications,
    prune_read_notifications,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def folder(db):
    return Folder.objects.create(
        name="GC domain", content_type=Folder.ContentType.DOMAIN
    )


@pytest.fixture
def user(db):
    return User.objects.create(email="gc@test.local")


def _row(user, control, *, is_read=False, age_days=0, type="expired_controls"):
    row = Notification.objects.create(
        recipient=user,
        type=type,
        context={"control_name": str(control)},
        content_type=ContentType.objects.get_for_model(AppliedControl),
        object_id=control.id,
        is_read=is_read,
    )
    if age_days:
        stamp = timezone.now() - timedelta(days=age_days)
        Notification.objects.filter(pk=row.pk).update(
            created_at=stamp, updated_at=stamp
        )
    return row


def test_retention_removes_read_rows_past_the_window(folder, user):
    old_read = _row(
        user,
        AppliedControl.objects.create(name="a", folder=folder),
        is_read=True,
        age_days=RETENTION_DAYS + 1,
    )
    assert prune_read_notifications() == 1
    assert not Notification.objects.filter(pk=old_read.pk).exists()


def test_retention_spares_unread_rows_however_old(folder, user):
    """An unread row is still asking for something; age does not make it irrelevant."""
    old_unread = _row(
        user,
        AppliedControl.objects.create(name="b", folder=folder),
        is_read=False,
        age_days=RETENTION_DAYS * 5,
    )
    assert prune_read_notifications() == 0
    assert Notification.objects.filter(pk=old_unread.pk).exists()


def test_retention_spares_recently_read_rows(folder, user):
    fresh = _row(
        user,
        AppliedControl.objects.create(name="c", folder=folder),
        is_read=True,
        age_days=RETENTION_DAYS - 1,
    )
    assert prune_read_notifications() == 0
    assert Notification.objects.filter(pk=fresh.pk).exists()


def test_cap_keeps_the_newest_and_drops_the_rest(folder, user, settings):
    control = AppliedControl.objects.create(name="d", folder=folder)
    # One row per type to stay clear of the natural key; ages make the order explicit.
    for i in range(MAX_PER_RECIPIENT + 5):
        _row(user, control, type=f"synthetic_{i}", age_days=i)
    assert Notification.objects.filter(recipient=user).count() == MAX_PER_RECIPIENT + 5

    assert enforce_per_recipient_cap() == 5
    remaining = Notification.objects.filter(recipient=user)
    assert remaining.count() == MAX_PER_RECIPIENT
    # The five oldest went; the newest survived.
    assert not remaining.filter(type=f"synthetic_{MAX_PER_RECIPIENT + 4}").exists()
    assert remaining.filter(type="synthetic_0").exists()


def test_cap_is_per_recipient_not_global(folder, user, db):
    other = User.objects.create(email="gc-other@test.local")
    control = AppliedControl.objects.create(name="e", folder=folder)
    _row(user, control)
    _row(other, control)
    assert enforce_per_recipient_cap() == 0
    assert Notification.objects.count() == 2


def test_orphans_go_when_their_target_does(folder, user):
    control = AppliedControl.objects.create(name="f", folder=folder)
    survivor = AppliedControl.objects.create(name="g", folder=folder)
    _row(user, control, type="expired_controls")
    kept = _row(user, survivor, type="expired_controls")

    control.delete()  # GFK has no DB cascade, so the row is still there
    assert Notification.objects.count() == 2

    assert prune_orphaned_notifications() == 1
    assert list(Notification.objects.values_list("pk", flat=True)) == [kept.pk]


def test_orphan_sweep_is_a_no_op_when_everything_is_alive(folder, user):
    control = AppliedControl.objects.create(name="h", folder=folder)
    _row(user, control)
    assert prune_orphaned_notifications() == 0
    assert Notification.objects.count() == 1


# --- the admin channel matrix ---------------------------------------------------------


def test_matrix_reports_every_type_with_its_ceiling():
    from notifications.channels import matrix
    from notifications.registry import NOTIFICATION_REGISTRY

    rows = matrix()
    assert len(rows) == len(NOTIFICATION_REGISTRY)
    by_type = {row["type"]: row for row in rows}
    # The registry is the ceiling: an email-only type can never report in_app.
    assert by_type["welcome"]["supports_in_app"] is False
    assert by_type["welcome"]["in_app"] is False
    assert by_type["expired_controls"]["supports_in_app"] is True


def test_narrowing_in_app_stops_notify_writing(folder, user):
    from notifications.channels import set_channel
    from notifications.service import notify

    control = AppliedControl.objects.create(name="matrix", folder=folder)
    set_channel("expired_controls", "in_app", False)
    assert notify("expired_controls", [user], control, {"control_name": "x"}) == []
    assert Notification.objects.count() == 0

    set_channel("expired_controls", "in_app", True)
    assert len(notify("expired_controls", [user], control, {"control_name": "x"})) == 1


def test_the_matrix_cannot_widen_beyond_the_registry():
    from notifications.channels import set_channel

    with pytest.raises(ValueError, match="does not support in_app"):
        set_channel("welcome", "in_app", True)


def test_email_column_reads_and_writes_the_existing_mute_list():
    """`disabled_email_templates` already governs email everywhere; the matrix edits
    that list rather than introducing a second source of truth."""
    from core.email_utils import get_disabled_email_templates
    from notifications.channels import matrix, set_channel

    set_channel("expired_controls", "email", False)
    assert "expired_controls" in get_disabled_email_templates()
    assert (
        next(r for r in matrix() if r["type"] == "expired_controls")["email"] is False
    )

    set_channel("expired_controls", "email", True)
    assert "expired_controls" not in get_disabled_email_templates()


def _bulk(user, n, *, is_read, prefix):
    """Rows straight into the table: the cap does not resolve targets, and 1000 saves
    through the ORM would dominate the test's runtime."""
    content_type = ContentType.objects.get_for_model(AppliedControl)
    rows = [
        Notification(
            recipient=user,
            type="expired_controls",
            context={"control_name": f"{prefix} {i}"},
            content_type=content_type,
            object_id=uuid4(),
            is_read=is_read,
        )
        for i in range(n)
    ]
    return Notification.objects.bulk_create(rows)


def test_the_cap_sacrifices_read_rows_before_unread(folder, user):
    """A full inbox should lose history, not work."""
    unread = _bulk(user, MAX_PER_RECIPIENT, is_read=False, prefix="unread")
    _bulk(user, 50, is_read=True, prefix="read")

    assert enforce_per_recipient_cap() == 50
    survivors = set(
        Notification.objects.filter(recipient=user).values_list("id", flat=True)
    )
    assert survivors == {n.id for n in unread}, (
        "every read row went, every unread stayed"
    )


def test_the_cap_still_bites_when_everything_is_unread(folder, user):
    """Otherwise a runaway producer, which writes unread, has no ceiling at all."""
    _bulk(user, MAX_PER_RECIPIENT + 20, is_read=False, prefix="flood")

    assert enforce_per_recipient_cap() == 20
    assert Notification.objects.filter(recipient=user).count() == MAX_PER_RECIPIENT
