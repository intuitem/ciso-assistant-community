"""
Evidence review wiring: moving an evidence to approved or rejected tells its owners,
one notification per evidence (SUP-1587).

Tasks are queued with `transaction.on_commit`, and HUEY runs with
`immediate: False`, so they are swapped for in-process `.call_local()` runs.
"""

from contextlib import contextmanager
from unittest.mock import patch

import pytest

from core.models import Evidence
from core.serializers import EvidenceWriteSerializer
from iam.models import Folder, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def folder(db):
    return Folder.objects.create(
        name="Evidence test domain", content_type=Folder.ContentType.DOMAIN
    )


@pytest.fixture
def owner(db):
    return User.objects.create(email="owner@test.local")


@pytest.fixture
def evidence(folder, owner):
    evidence = Evidence.objects.create(
        name="Firewall export", folder=folder, status=Evidence.Status.IN_REVIEW
    )
    evidence.owner.add(owner.actor)
    return evidence


@contextmanager
def _producer(django_capture_on_commit_callbacks):
    from core import tasks

    task = tasks.send_evidence_reviewed_notification
    with (
        patch(
            "core.tasks.send_evidence_reviewed_notification",
            side_effect=lambda *a: task.call_local(*a),
        ),
        patch("core.tasks.check_email_configuration", return_value=True),
        patch("core.tasks.notify") as notify,
        patch("core.tasks.send_notification_email") as send_email,
        django_capture_on_commit_callbacks(execute=True),
    ):
        yield notify, send_email


def _set_status(evidence, status):
    serializer = EvidenceWriteSerializer(
        evidence, data={"status": status}, partial=True
    )
    assert serializer.is_valid(), serializer.errors
    return serializer.save()


@pytest.mark.parametrize("status", ["approved", "rejected"])
def test_review_tells_the_owners(
    evidence, owner, status, django_capture_on_commit_callbacks
):
    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        _set_status(evidence, status)

    notification_type, recipients, target, context = notify.call_args.args
    assert notification_type == "evidence_reviewed"
    assert recipients == [owner.email]
    assert target == evidence
    assert context == {"evidence_name": "Firewall export", "decision_key": status}

    subject, _body, recipient, _html = send_email.call_args.args
    assert recipient == owner.email
    assert subject.endswith(f": {status.capitalize()}"), subject


@pytest.mark.parametrize("status", ["in_review", "draft", "missing"])
def test_other_statuses_send_nothing(
    evidence, status, django_capture_on_commit_callbacks
):
    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        _set_status(evidence, status)

    notify.assert_not_called()
    send_email.assert_not_called()


def test_saving_an_already_rejected_evidence_sends_nothing(
    evidence, django_capture_on_commit_callbacks
):
    _set_status(evidence, "rejected")
    with _producer(django_capture_on_commit_callbacks) as (notify, _send_email):
        _set_status(evidence, "rejected")

    notify.assert_not_called()


def test_email_is_in_the_owner_language(evidence, django_capture_on_commit_callbacks):
    with (
        patch("core.email_utils.get_email_preferences", return_value=("fr", "auto")),
        _producer(django_capture_on_commit_callbacks) as (_notify, send_email),
    ):
        _set_status(evidence, "approved")

    assert send_email.call_args.args[0].endswith(": Approuvé")
