"""Viewset edges. Ids arrive from the client, so they are not known to be UUIDs —
filtering a UUIDField on a malformed string raises Django's ValidationError, which DRF
does not map to a 400. Both of these were authenticated 500s.
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
def user(db):
    return User.objects.create(email="viewset@test.local")


@pytest.fixture
def row(user):
    folder = Folder.objects.create(
        name="Viewset domain", content_type=Folder.ContentType.DOMAIN
    )
    control = AppliedControl.objects.create(name="Rotate keys", folder=folder)
    notify("expired_controls", [user], control, {"control_name": control.name})
    return Notification.objects.get()


def get(user, **params):
    request = factory.get("/api/notifications/", params)
    force_authenticate(request, user=user)
    response = NotificationViewSet.as_view({"get": "list"})(request)
    response.render()
    return response


def post_batch(user, payload):
    request = factory.post("/api/notifications/batch-action", payload, format="json")
    force_authenticate(request, user=user)
    response = NotificationViewSet.as_view({"post": "batch_action"})(request)
    response.render()
    return response


def test_malformed_folder_filter_is_empty_not_a_crash(user, row):
    response = get(user, folder="not-a-uuid")
    assert response.status_code == 200
    assert response.data["results"] == []


def test_malformed_batch_id_is_reported_as_failed(user, row):
    response = post_batch(
        user,
        {
            "action": "change_field",
            "field": "is_read",
            "value": "true",
            "ids": ["not-a-uuid", str(row.id)],
        },
    )
    assert response.status_code == 200
    assert [f["id"] for f in response.data["failed"]] == ["not-a-uuid"]
    assert [s["id"] for s in response.data["succeeded"]] == [str(row.id)]
    row.refresh_from_db()
    assert row.is_read is True


def channel_post(user, payload):
    from notifications.views import NotificationChannelsView

    request = factory.post("/api/notification-channels/", payload, format="json")
    force_authenticate(request, user=user)
    response = NotificationChannelsView.as_view()(request)
    response.render()
    return response


@pytest.fixture
def admin(db):
    """`IsGlobalAdmin` asks `user.is_admin()`, which is BI-UG-ADM membership --
    `is_superuser` alone is not enough."""
    from core.startup import startup
    from iam.models import UserGroup

    startup(sender=None)
    user = User.objects.create_superuser("channels-admin@test.local")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    user.folder = admin_group.folder
    user.save()
    admin_group.user_set.add(user)
    return user


@pytest.mark.parametrize("enabled", ["false", "true", 0, 1, None, "", "yes"])
def test_a_non_boolean_enabled_is_rejected(admin, enabled):
    """bool("false") is True, so coercing would switch the channel on when the caller
    asked for off."""
    response = channel_post(
        admin, {"type": "expired_controls", "channel": "in_app", "enabled": enabled}
    )
    assert response.status_code == 400


def test_a_real_boolean_is_applied(admin):
    from notifications.channels import in_app_allowed

    assert (
        channel_post(
            admin, {"type": "expired_controls", "channel": "in_app", "enabled": False}
        ).status_code
        == 200
    )
    assert in_app_allowed("expired_controls") is False


def test_a_rejected_change_does_not_echo_the_exception(admin):
    """The detail belongs in the log, not the response body."""
    response = channel_post(
        admin, {"type": "no_such_type", "channel": "in_app", "enabled": True}
    )
    assert response.status_code == 400
    assert "no_such_type" not in str(response.data)
