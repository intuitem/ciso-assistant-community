"""A validation outcome carries onto the linked exceptions."""

import pytest

from core.models import SecurityException, ValidationFlow
from core.serializers import (
    SecurityExceptionWriteSerializer,
    ValidationFlowWriteSerializer,
)
from iam.models import Folder, User

sync = ValidationFlowWriteSerializer()._sync_security_exception_status


@pytest.mark.django_db
@pytest.mark.parametrize(
    "start,decision,expected",
    [
        ("in_review", "accepted", "approved"),
        ("in_review", "rejected", "rejected"),
        ("approved", "revoked", "in_review"),
        ("in_review", "revoked", "in_review"),
        ("in_review", "change_requested", "in_review"),
    ],
)
def test_outcome_updates_linked_exceptions(start, decision, expected):
    folder = Folder.get_root_folder()
    flow = ValidationFlow.objects.create(
        folder=folder, approver=User.objects.create(email="approver@test.local")
    )
    linked = SecurityException.objects.create(
        name="linked", folder=folder, status=start
    )
    resolved = SecurityException.objects.create(
        name="resolved", folder=folder, status="resolved"
    )
    flow.security_exceptions.add(linked, resolved)

    sync(flow, "submitted", decision)

    linked.refresh_from_db()
    resolved.refresh_from_db()
    assert linked.status == expected
    assert resolved.status == "resolved"


@pytest.mark.django_db
def test_changed_exceptions_notify_owners(monkeypatch):
    notified = []
    monkeypatch.setattr(
        SecurityExceptionWriteSerializer,
        "_send_status_notification",
        lambda self, exception: notified.append(exception.name),
    )
    folder = Folder.get_root_folder()
    flow = ValidationFlow.objects.create(
        folder=folder, approver=User.objects.create(email="approver@test.local")
    )
    flow.security_exceptions.add(
        SecurityException.objects.create(name="linked", folder=folder),
        SecurityException.objects.create(
            name="resolved", folder=folder, status="resolved"
        ),
    )

    sync(flow, "submitted", "accepted")

    assert notified == ["linked"]
