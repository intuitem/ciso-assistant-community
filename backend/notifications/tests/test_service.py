import pytest
from django.contrib.contenttypes.models import ContentType

from core.models import AppliedControl
from iam.models import Folder, User
from notifications.models import Notification
from notifications.service import clear_stale, in_app_enabled, notify

pytestmark = pytest.mark.django_db


@pytest.fixture
def folder(db):
    return Folder.objects.create(
        name="Notif test domain", content_type=Folder.ContentType.DOMAIN
    )


@pytest.fixture
def control(folder):
    return AppliedControl.objects.create(name="Encrypt backups", folder=folder)


@pytest.fixture
def user(db):
    return User.objects.create(email="recipient@test.local")


def rows(user=None):
    qs = Notification.objects.all()
    return qs.filter(recipient=user) if user else qs


def test_writes_one_row_with_its_context(user, control):
    assert (
        len(notify("expired_controls", [user], control, {"control_name": control.name}))
        == 1
    )
    row = rows(user).get()
    assert row.context == {"control_name": "Encrypt backups"}
    assert row.is_read is False
    assert row.target == control
    assert row.folder == control.folder


def test_accepts_an_email_address_as_recipient(user, control):
    """Producers group by email, not by User."""
    assert (
        len(notify("expired_controls", [user.email], control, {"control_name": "x"}))
        == 1
    )
    assert rows(user).count() == 1


def test_upsert_is_keyed_on_recipient_type_and_target(user, control):
    for _ in range(3):
        notify("expired_controls", [user], control, {"control_name": control.name})
    assert rows(user).count() == 1


def test_a_condition_refire_does_not_reopen_a_read_row(user, control):
    notify("expired_controls", [user], control, {"control_name": control.name})
    rows(user).update(is_read=True)
    notify("expired_controls", [user], control, {"control_name": control.name})
    assert rows(user).get().is_read is True, "read is the latch that stops the nag"


def test_an_event_refire_does_reopen_a_read_row(user, control):
    notify(
        "applied_control_assignment", [user], control, {"control_name": control.name}
    )
    rows(user).update(is_read=True)
    notify(
        "applied_control_assignment", [user], control, {"control_name": control.name}
    )
    assert rows(user).get().is_read is False, "being assigned again is new information"


def test_an_email_only_type_writes_nothing(user, control):
    assert in_app_enabled("welcome") is False
    assert notify("welcome", [user], control, {}) == []
    assert rows().count() == 0


def test_an_unknown_type_writes_nothing(user, control):
    assert notify("no_such_type", [user], control, {}) == []
    assert rows().count() == 0


def test_a_target_without_a_folder_is_refused(user):
    """FolderMixin defaults to the root folder rather than raising, so a missing
    folder would silently expose the row to every root-level role."""
    orphan = ContentType.objects.get_for_model(ContentType)
    assert notify("expired_controls", [user], orphan, {"control_name": "x"}) == []
    assert rows().count() == 0


def test_a_missing_context_variable_still_writes_a_row(user, control):
    """The title renders client-side, so a producer that forgets a variable leaves a
    gap in one row rather than losing the notification."""
    assert len(notify("expired_controls", [user], control, {})) == 1
    assert rows(user).get().context == {}


def test_third_party_users_get_no_inbox(control, db):
    tp = User.objects.create(email="third@party.local", is_third_party=True)
    assert notify("expired_controls", [tp], control, {"control_name": "x"}) == []


def test_clear_stale_deletes_what_the_sweep_no_longer_sees(user, control, folder):
    other = AppliedControl.objects.create(name="Rotate keys", folder=folder)
    notify("expired_controls", [user], control, {"control_name": control.name})
    notify("expired_controls", [user], other, {"control_name": other.name})
    assert rows(user).count() == 2

    assert clear_stale("expired_controls", {(user.id, control.id)}) == 1
    assert [n.object_id for n in rows(user)] == [control.id]


def test_clearing_re_arms_the_type(user, control):
    """A deleted row frees the natural key, so a recurrence is unread again --
    the re-arm rule, with no armed column and no tombstone."""
    notify("expired_controls", [user], control, {"control_name": control.name})
    rows(user).update(is_read=True)
    clear_stale("expired_controls", set())
    assert rows(user).count() == 0

    notify("expired_controls", [user], control, {"control_name": control.name})
    assert rows(user).get().is_read is False


def test_clear_stale_refuses_an_event_type(user, control):
    notify("applied_control_assignment", [user], control, {"control_name": "x"})
    assert clear_stale("applied_control_assignment", set()) == 0
    assert rows(user).count() == 1, (
        "events are not swept; they leave by user or retention"
    )


def test_clear_stale_is_scoped_to_its_own_type(user, control):
    notify("expired_controls", [user], control, {"control_name": "x"})
    notify("applied_control_assignment", [user], control, {"control_name": "x"})
    clear_stale("expired_controls", set())
    assert [n.type for n in rows(user)] == ["applied_control_assignment"]
