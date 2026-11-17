"""A validation outcome carries onto the linked exceptions."""

import pytest

from core.apps import startup
from core.models import SecurityException, ValidationFlow
from core.serializers import (
    SecurityExceptionWriteSerializer,
    ValidationFlowWriteSerializer,
)
from iam.models import Folder, User, UserGroup

sync = ValidationFlowWriteSerializer()._sync_security_exception_status


@pytest.fixture
def requester(db):
    startup(sender=None, **{})
    user = User.objects.create_user(email="requester@test.local")
    UserGroup.objects.get(name="BI-UG-ADM").user_set.add(user)
    return user


def make_flow(requester, status="submitted"):
    return ValidationFlow.objects.create(
        folder=Folder.get_root_folder(),
        requester=requester,
        approver=User.objects.create(email=f"approver-{status}@test.local"),
        status=status,
    )


def make_exception(name, status="in_review"):
    return SecurityException.objects.create(
        name=name, folder=Folder.get_root_folder(), status=status
    )


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
def test_outcome_updates_linked_exceptions(requester, start, decision, expected):
    flow = make_flow(requester)
    linked = make_exception("linked", start)
    resolved = make_exception("resolved", "resolved")
    flow.security_exceptions.add(linked, resolved)

    sync(flow, "submitted", decision)

    linked.refresh_from_db()
    resolved.refresh_from_db()
    assert linked.status == expected
    assert resolved.status == "resolved"


@pytest.mark.django_db
def test_requester_without_change_right_leaves_exception(requester):
    flow = make_flow(User.objects.create_user(email="viewer@test.local"))
    linked = make_exception("linked")
    flow.security_exceptions.add(linked)

    sync(flow, "submitted", "accepted")

    linked.refresh_from_db()
    assert linked.status == "in_review"


@pytest.mark.django_db
def test_revoke_keeps_exception_approved_by_another_flow(requester):
    shared = make_exception("shared", "approved")
    revoked = make_flow(requester, "revoked")
    make_flow(requester, "accepted").security_exceptions.add(shared)
    revoked.security_exceptions.add(shared)

    sync(revoked, "accepted", "revoked")

    shared.refresh_from_db()
    assert shared.status == "approved"


@pytest.mark.django_db
def test_changed_exceptions_notify_owners(requester, monkeypatch):
    notified = []
    monkeypatch.setattr(
        SecurityExceptionWriteSerializer,
        "_send_status_notification",
        lambda self, exception: notified.append(exception.name),
    )
    flow = make_flow(requester)
    flow.security_exceptions.add(
        make_exception("linked"), make_exception("resolved", "resolved")
    )

    sync(flow, "submitted", "accepted")

    assert notified == ["linked"]
