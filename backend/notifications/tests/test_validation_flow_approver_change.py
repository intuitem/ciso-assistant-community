"""
Handing a pending validation flow to another approver asks the new approver (reusing
`validation_flow_created`) and drops the old approver's request row.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core.models import ValidationFlow
from core.serializers import ValidationFlowWriteSerializer
from iam.models import Folder, User
from notifications.models import Notification

pytestmark = pytest.mark.django_db


@pytest.fixture
def folder(db):
    return Folder.objects.create(
        name="Validation test domain", content_type=Folder.ContentType.DOMAIN
    )


@pytest.fixture
def requester(db):
    # Superuser so the serializer's folder permission check passes.
    return User.objects.create_superuser("requester@test.local")


@pytest.fixture
def old_approver(db):
    return User.objects.create(email="old@test.local")


@pytest.fixture
def new_approver(db):
    return User.objects.create(email="new@test.local")


@pytest.fixture
def flow(folder, requester, old_approver):
    flow = ValidationFlow.objects.create(
        folder=folder, requester=requester, approver=old_approver
    )
    Notification.objects.create(
        recipient=old_approver, type="validation_flow_created", target=flow
    )
    return flow


def _patch(flow, user, data):
    serializer = ValidationFlowWriteSerializer(
        flow,
        data=data,
        partial=True,
        context={"request": SimpleNamespace(user=user)},
    )
    assert serializer.is_valid(), serializer.errors
    return serializer.save()


def test_new_approver_is_asked_and_old_row_dropped(
    flow, requester, old_approver, new_approver, django_capture_on_commit_callbacks
):
    with (
        patch("core.tasks.send_validation_flow_created_notification") as send,
        django_capture_on_commit_callbacks(execute=True),
    ):
        _patch(flow, requester, {"approver": str(new_approver.id)})

    send.assert_called_once()
    assert send.call_args.args[0].approver == new_approver
    assert not Notification.objects.filter(recipient=old_approver).exists()


def test_same_approver_sends_nothing(
    flow, requester, old_approver, django_capture_on_commit_callbacks
):
    with (
        patch("core.tasks.send_validation_flow_created_notification") as send,
        django_capture_on_commit_callbacks(execute=True),
    ):
        _patch(flow, requester, {"request_notes": "more context"})

    send.assert_not_called()
    assert Notification.objects.filter(recipient=old_approver).exists()


def test_closed_flow_reassignment_sends_nothing(
    flow, requester, new_approver, django_capture_on_commit_callbacks
):
    ValidationFlow.objects.filter(pk=flow.pk).update(
        status=ValidationFlow.Status.ACCEPTED
    )
    flow.refresh_from_db()
    with (
        patch("core.tasks.send_validation_flow_created_notification") as send,
        django_capture_on_commit_callbacks(execute=True),
    ):
        _patch(flow, requester, {"approver": str(new_approver.id)})

    send.assert_not_called()


def test_resubmit_with_new_approver_is_not_announced_twice(
    flow, requester, new_approver, django_capture_on_commit_callbacks
):
    """The status-change notice already reaches the new approver."""
    ValidationFlow.objects.filter(pk=flow.pk).update(
        status=ValidationFlow.Status.CHANGE_REQUESTED
    )
    flow.refresh_from_db()
    with (
        patch("core.tasks.send_validation_flow_created_notification") as created,
        patch("core.tasks.send_validation_flow_updated_notification") as updated,
        django_capture_on_commit_callbacks(execute=True),
    ):
        _patch(
            flow,
            requester,
            {"status": "submitted", "approver": str(new_approver.id)},
        )

    created.assert_not_called()
    assert updated.call_args.args[1] == new_approver.email


def test_queued_request_goes_to_the_approver_current_at_run_time(
    flow, old_approver, new_approver
):
    """The task gets the flow pickled at enqueue; it must reload before notifying."""
    from core.tasks import send_validation_flow_created_notification

    stale = ValidationFlow.objects.get(pk=flow.pk)
    ValidationFlow.objects.filter(pk=flow.pk).update(approver=new_approver)
    with (
        patch("core.tasks.check_email_configuration", return_value=False),
        patch("core.tasks.notify") as notify,
    ):
        send_validation_flow_created_notification.call_local(stale)

    assert notify.call_args.args[1] == [new_approver.email]


def test_queued_request_for_a_deleted_flow_sends_nothing(flow):
    from core.tasks import send_validation_flow_created_notification

    stale = ValidationFlow.objects.get(pk=flow.pk)
    ValidationFlow.objects.filter(pk=flow.pk).delete()
    with patch("core.tasks.notify") as notify:
        send_validation_flow_created_notification.call_local(stale)

    notify.assert_not_called()
