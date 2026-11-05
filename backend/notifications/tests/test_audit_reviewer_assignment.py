"""
Audit reviewer wiring: ComplianceAssessmentWriteSerializer notifies the reviewers it
adds, and only those (SUP-639). Authors keep their own type.

Tasks are queued with `transaction.on_commit`, and HUEY runs with
`immediate: False`, so they are swapped for in-process `.call_local()` runs.
"""

from contextlib import contextmanager
from unittest.mock import patch

import pytest

from core.models import ComplianceAssessment, Framework
from core.serializers import ComplianceAssessmentWriteSerializer
from iam.models import Folder, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def folder(db):
    return Folder.objects.create(
        name="Audit test domain", content_type=Folder.ContentType.DOMAIN
    )


@pytest.fixture
def framework(folder):
    return Framework.objects.create(
        name="Reviewer fw", urn="urn:test:framework:reviewer", folder=folder
    )


@pytest.fixture
def alice(db):
    return User.objects.create(email="alice@test.local")


@pytest.fixture
def bob(db):
    return User.objects.create(email="bob@test.local")


@contextmanager
def _producer(django_capture_on_commit_callbacks):
    from core import tasks

    task = tasks.send_compliance_assessment_reviewer_assignment_notification
    with (
        patch(
            "core.tasks.send_compliance_assessment_reviewer_assignment_notification",
            side_effect=lambda *a: task.call_local(*a),
        ),
        patch("core.tasks.send_compliance_assessment_assignment_notification"),
        patch("core.tasks.check_email_configuration", return_value=True),
        patch("core.tasks.notify") as notify,
        patch("core.tasks.send_notification_email") as send_email,
        django_capture_on_commit_callbacks(execute=True),
    ):
        yield notify, send_email


def _save(data, instance=None) -> ComplianceAssessment:
    serializer = ComplianceAssessmentWriteSerializer(
        instance, data=data, partial=bool(instance)
    )
    assert serializer.is_valid(), serializer.errors
    return serializer.save()


def _actor_ids(*users):
    return [str(u.actor.id) for u in users]


def _create(folder, framework, reviewers) -> ComplianceAssessment:
    return _save(
        {
            "name": "ISO audit",
            "folder": str(folder.id),
            "framework": str(framework.id),
            "reviewers": _actor_ids(*reviewers),
        }
    )


def test_create_notifies_the_reviewers(
    folder, framework, alice, django_capture_on_commit_callbacks
):
    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        audit = _create(folder, framework, [alice])

    notification_type, recipients, target, context = notify.call_args.args
    assert notification_type == "compliance_assessment_reviewer_assignment"
    assert recipients == [alice.email]
    assert target == audit
    assert context["assessment_name"] == "ISO audit"

    subject, _body, recipient, _html = send_email.call_args.args
    assert recipient == alice.email
    assert "reviewer" in subject


def test_update_notifies_only_the_new_reviewer(
    folder, framework, alice, bob, django_capture_on_commit_callbacks
):
    audit = _create(folder, framework, [alice])

    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        _save({"reviewers": _actor_ids(alice, bob)}, audit)

    notify.assert_called_once()
    assert notify.call_args.args[1] == [bob.email]
    send_email.assert_called_once()


def test_unchanged_reviewers_send_nothing(
    folder, framework, alice, django_capture_on_commit_callbacks
):
    audit = _create(folder, framework, [alice])

    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        _save({"name": "ISO audit v2", "reviewers": _actor_ids(alice)}, audit)

    notify.assert_not_called()
    send_email.assert_not_called()
