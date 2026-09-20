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
