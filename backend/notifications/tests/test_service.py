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


def test_the_folder_follows_the_target(user, control, folder):
    """The folder is derived, never stored: moving the target moves the notification
    with it, which is the whole reason the column went away."""
    notify("expired_controls", [user], control, {"control_name": control.name})
    assert rows(user).get().folder == folder

    moved = Folder.objects.create(
        name="Elsewhere", content_type=Folder.ContentType.DOMAIN
    )
    control.folder = moved
    control.save()
    assert rows(user).get().folder == moved


def test_a_target_without_a_folder_still_notifies(user):
    """Nothing gates on the folder, so a folderless target is no longer a refusal —
    it simply has no domain to report."""
    orphan = ContentType.objects.get_for_model(ContentType)
    assert len(notify("expired_controls", [user], orphan, {"control_name": "x"})) == 1
    assert rows(user).get().folder is None


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


def test_the_feature_flag_stops_rows_being_written(user, control, monkeypatch):
    """Off means nothing is written, not written-and-hidden: filtering on read would
    accumulate invisible rows and hand the GC a backlog for an unused feature."""
    import notifications.service as service

    monkeypatch.setattr(service, "ff_is_enabled", lambda flag: False)
    assert notify("expired_controls", [user], control, {"control_name": "x"}) == []
    assert rows().count() == 0

    monkeypatch.setattr(service, "ff_is_enabled", lambda flag: True)
    assert len(notify("expired_controls", [user], control, {"control_name": "x"})) == 1


# --- read_at ---------------------------------------------------------------------------


def test_read_at_is_stamped_on_the_transition_only(user, control):
    """ "When did I read this" must not move every time the row is touched."""
    notify("expired_controls", [user], control, {"control_name": "x"})
    row = rows(user).get()
    assert row.read_at is None

    Notification.set_read(rows(user), True)
    first = rows(user).get().read_at
    assert first is not None

    # Marking an already-read row read again leaves the original stamp alone.
    Notification.set_read(rows(user), True)
    assert rows(user).get().read_at == first


def test_marking_unread_clears_read_at(user, control):
    notify("expired_controls", [user], control, {"control_name": "x"})
    Notification.set_read(rows(user), True)
    assert rows(user).get().read_at is not None

    Notification.set_read(rows(user), False)
    row = rows(user).get()
    assert row.is_read is False and row.read_at is None


def test_an_event_refire_clears_read_at_with_the_unread_flip(user, control):
    """The row is asking again, so the old read time no longer describes it."""
    notify("applied_control_assignment", [user], control, {"control_name": "x"})
    Notification.set_read(rows(user), True)
    assert rows(user).get().read_at is not None

    notify("applied_control_assignment", [user], control, {"control_name": "x"})
    row = rows(user).get()
    assert row.is_read is False and row.read_at is None


def test_a_condition_refire_leaves_a_read_row_and_its_stamp_alone(user, control):
    notify("expired_controls", [user], control, {"control_name": "x"})
    Notification.set_read(rows(user), True)
    stamp = rows(user).get().read_at

    notify("expired_controls", [user], control, {"control_name": "x"})
    row = rows(user).get()
    assert row.is_read is True and row.read_at == stamp


# --- the badge gets its count from the mutation, not a second request ------------------


@pytest.mark.parametrize("path", ["detail", "batch"])
def test_mutation_responses_report_the_new_unread_count(user, control, folder, path):
    """Marking rows read inside the inbox never navigates, so the badge has no other
    cue; the response carries the count rather than the client guessing."""
    from rest_framework.test import APIClient

    from core.models import AppliedControl

    others = [
        AppliedControl.objects.create(name=f"unread-{i}", folder=folder)
        for i in range(3)
    ]
    for target in [control, *others]:
        notify("expired_controls", [user], target, {"control_name": str(target)})
    assert rows(user).filter(is_read=False).count() == 4

    client = APIClient()
    client.force_authenticate(user=user)
    row = rows(user).first()

    if path == "detail":
        response = client.patch(
            f"/api/notifications/{row.id}/",
            {"is_read": True},
            format="json",
            HTTP_HOST="localhost",
        )
        expected = 3
    else:
        response = client.post(
            "/api/notifications/batch-action/",
            {
                "action": "change_field",
                "field": "is_read",
                "value": "true",
                "ids": [str(r.id) for r in rows(user)[:2]],
            },
            format="json",
            HTTP_HOST="localhost",
        )
        expected = 2

    assert response.status_code == 200
    assert response.data["unread_count"] == expected
    assert rows(user).filter(is_read=False).count() == expected


def test_recipient_count_is_the_size_of_the_in_app_audience(control):
    alice = User.objects.create(email="alice@test.local")
    bob = User.objects.create(email="bob@test.local")
    carol = User.objects.create(email="carol@test.local")

    notify("expired_controls", [alice, bob, carol], control, {})

    assert {r.recipient_count for r in rows()} == {3}


def test_recipient_count_ignores_addresses_with_no_user(control, user):
    """A team's shared mailbox is in get_emails() but is not a User, so it gets the
    email and no inbox row -- it must not inflate the count either."""
    notify("expired_controls", [user.email, "team-mailbox@test.local"], control, {})

    assert rows().get().recipient_count == 1


def test_recipient_count_follows_the_audience_on_a_re_fire(control, user):
    notify("expired_controls", [user], control, {})
    assert rows().get().recipient_count == 1

    later = User.objects.create(email="joined@test.local")
    notify("expired_controls", [user, later], control, {})

    assert {r.recipient_count for r in rows()} == {2}
