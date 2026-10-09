"""
Incident assignment wiring: IncidentWriteSerializer notifies owners it adds, and
only those.

The task is queued with `transaction.on_commit`, and HUEY runs with
`immediate: False`, so the task is swapped for one that runs in-process with
`.call_local()`.
"""

from contextlib import contextmanager
from unittest.mock import patch

import pytest

from core.models import Incident
from core.serializers import IncidentWriteSerializer
from iam.models import Folder, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def folder(db):
    return Folder.objects.create(
        name="Incident test domain", content_type=Folder.ContentType.DOMAIN
    )


@pytest.fixture
def alice(db):
    return User.objects.create(email="alice@test.local")


@pytest.fixture
def bob(db):
    return User.objects.create(email="bob@test.local")


@contextmanager
def _producer(django_capture_on_commit_callbacks):
    """Run the commit callbacks, and the task they queue, in-process. Yields the
    `notify` and `send_notification_email` mocks."""
    from core import tasks

    task = tasks.send_incident_assignment_notification
    with (
        patch(
            "core.tasks.send_incident_assignment_notification",
            side_effect=lambda *args: task.call_local(*args),
        ),
        patch("core.tasks.check_email_configuration", return_value=True),
        patch("core.tasks.notify") as notify,
        patch("core.tasks.send_notification_email") as send_email,
        django_capture_on_commit_callbacks(execute=True),
    ):
        yield notify, send_email


def _save(data, instance=None) -> Incident:
    serializer = IncidentWriteSerializer(instance, data=data, partial=bool(instance))
    assert serializer.is_valid(), serializer.errors
    return serializer.save()


def _create(folder, owners) -> Incident:
    return _save(
        {
            "name": "Payroll breach",
            "description": "Attacker exfiltrated the payroll database",
            "folder": str(folder.id),
            "owners": [str(user.actor.id) for user in owners],
        }
    )


def test_create_notifies_the_owners(folder, alice, django_capture_on_commit_callbacks):
    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        incident = _create(folder, [alice])

    notify.assert_called_once()
    notification_type, recipients, target, context = notify.call_args.args
    assert notification_type == "incident_assignment"
    assert recipients == [alice.email]
    assert target == incident
    assert context["incident_name"] == "Payroll breach"

    send_email.assert_called_once()
    subject, body, recipient, _html = send_email.call_args.args
    assert recipient == alice.email
    assert "Payroll breach" in subject
    assert "exfiltrated" not in body, "the description must stay out of the email"


def test_update_notifies_only_the_new_owner(
    folder, alice, bob, django_capture_on_commit_callbacks
):
    incident = _create(folder, [alice])

    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        _save({"owners": [str(alice.actor.id), str(bob.actor.id)]}, incident)

    notify.assert_called_once()
    assert notify.call_args.args[1] == [bob.email]
    send_email.assert_called_once()
    assert send_email.call_args.args[2] == bob.email


def test_update_with_unchanged_owners_sends_nothing(
    folder, alice, django_capture_on_commit_callbacks
):
    incident = _create(folder, [alice])

    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        _save(
            {"name": "Payroll breach (contained)", "owners": [str(alice.actor.id)]},
            incident,
        )

    notify.assert_not_called()
    send_email.assert_not_called()
