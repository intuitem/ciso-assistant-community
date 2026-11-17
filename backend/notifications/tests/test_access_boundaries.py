"""Access is the recipient and nothing else (ADR notification-recipient-scoped-access).

Both halves of that trade are load-bearing, so both are asserted here: a recipient with
no role in the target's domain reads their own row, and no role-holder reads anyone's.
"""

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from core.models import AppliedControl
from iam.models import Folder, User
from notifications.models import Notification
from notifications.service import notify
from notifications.views import NotificationViewSet

pytestmark = pytest.mark.django_db

factory = APIRequestFactory()


@pytest.fixture
def alice(db):
    return User.objects.create(email="alice@boundaries.local")


@pytest.fixture
def admin(db):
    """Outranks every domain role: if this user cannot reach Alice's inbox, none can."""
    from core.startup import startup
    from iam.models import UserGroup

    startup(sender=None)
    user = User.objects.create_superuser("admin@boundaries.local")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    user.folder = admin_group.folder
    user.save()
    admin_group.user_set.add(user)
    return user


@pytest.fixture
def reader(row):
    """A Reader in the target's domain -- the lowest role granted `delete_notification`."""
    from iam.models import Role, RoleAssignment, UserGroup

    domain = row.target.folder
    user = User.objects.create(email="reader@boundaries.local")
    group = UserGroup.objects.create(folder=domain, name="boundaries-readers")
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name="BI-RL-AUD"),
        folder=Folder.get_root_folder(),
        is_recursive=True,
    )
    assignment.perimeter_folders.add(domain)
    group.user_set.add(user)
    return user


@pytest.fixture
def row(alice):
    """Alice holds no role anywhere, so the target's domain is one she cannot browse."""
    folder = Folder.objects.create(
        name="Someone else's domain", content_type=Folder.ContentType.DOMAIN
    )
    control = AppliedControl.objects.create(name="Rotate keys", folder=folder)
    notify("expired_controls", [alice], control, {"control_name": control.name})
    return Notification.objects.get()


def call(user, view_map, method, pk=None, **kwargs):
    request = getattr(factory, method)("/api/notifications/", **kwargs)
    force_authenticate(request, user=user)
    response = NotificationViewSet.as_view(view_map)(request, pk=pk)
    response.render()
    return response


def listing(user):
    return call(user, {"get": "list"}, "get")


def test_a_recipient_with_no_role_in_the_domain_still_reads_their_own_row(alice, row):
    """The reason folder RBAC was dropped."""
    response = listing(alice)
    assert response.status_code == 200
    assert [r["id"] for r in response.data["results"]] == [str(row.id)]
    assert call(alice, {"get": "retrieve"}, "get", str(row.id)).status_code == 200


def test_a_global_admin_reads_nobody_elses_inbox(admin, row):
    """There is no admin read path, by design."""
    assert listing(admin).data["results"] == []
    assert call(admin, {"get": "retrieve"}, "get", str(row.id)).status_code == 404


def test_another_users_row_cannot_be_marked_read(admin, row):
    response = call(
        admin,
        {"patch": "partial_update"},
        "patch",
        str(row.id),
        data={"is_read": True},
        format="json",
    )
    assert response.status_code == 404
    row.refresh_from_db()
    assert row.is_read is False


def test_another_users_row_cannot_be_deleted(admin, row):
    assert call(admin, {"delete": "destroy"}, "delete", str(row.id)).status_code == 404
    assert Notification.objects.filter(pk=row.pk).exists()


def test_batch_action_reports_someone_elses_id_as_not_found(admin, row):
    """A foreign id is absent from the queryset rather than refused, and stays intact."""
    request = factory.post(
        "/api/notifications/batch-action",
        {"action": "delete", "ids": [str(row.id)]},
        format="json",
    )
    force_authenticate(request, user=admin)
    response = NotificationViewSet.as_view({"post": "batch_action"})(request)
    response.render()

    assert response.data["succeeded"] == []
    assert [f["id"] for f in response.data["failed"]] == [str(row.id)]
    assert Notification.objects.filter(pk=row.pk).exists()


def test_the_inbox_cannot_be_written_to(alice):
    """Notifications are system-generated; a POST would let a user forge one."""
    assert (
        call(alice, {"post": "create"}, "post", data={}, format="json").status_code
        == 405
    )


def test_cascade_info_answers_the_recipient(alice, row):
    """The regression: `DeleteConfirmModal` fetches this on mount, and the inherited
    version refused a recipient holding no role in the target's domain."""
    response = call(alice, {"get": "cascade_info"}, "get", str(row.id))
    assert response.status_code == 200
    assert [bucket["count"] for bucket in response.data.values()] == [0, 0, 0]


def test_cascade_info_is_recipient_scoped_too(admin, row):
    assert call(admin, {"get": "cascade_info"}, "get", str(row.id)).status_code == 404


def test_cascade_info_ignores_a_role_in_the_targets_domain(reader, row):
    """Holding the permission the inherited version asked for is not being the
    recipient, and no endpoint may read the row on that basis."""
    assert call(reader, {"get": "cascade_info"}, "get", str(row.id)).status_code == 404
    assert listing(reader).data["results"] == []
