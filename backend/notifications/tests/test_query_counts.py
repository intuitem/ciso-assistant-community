"""The two places this feature can degrade into an N+1.

Both are asserted as *constant* rather than as a magic number: the point is that
the count does not move with the number of rows, so each test measures twice.
"""

from itertools import count

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIRequestFactory, force_authenticate

from core.models import AppliedControl
from iam.models import Folder, User
from notifications.serializers import NotificationReadSerializer
from notifications.models import Notification
from notifications.service import notify_many
from notifications.views import NotificationViewSet

pytestmark = pytest.mark.django_db


@pytest.fixture
def folder(db):
    return Folder.objects.create(
        name="Query count domain", content_type=Folder.ContentType.DOMAIN
    )


@pytest.fixture
def user(db):
    return User.objects.create(email="counter@test.local")


_seq = count()


def controls(folder, n):
    return [
        AppliedControl.objects.create(name=f"Control {next(_seq)}", folder=folder)
        for _ in range(n)
    ]


def queries(fn):
    connection.queries_log.clear()
    with CaptureQueriesContext(connection) as ctx:
        fn()
    return [e for e in ctx.captured_queries if "SAVEPOINT" not in e["sql"].upper()]


def test_inbox_serialization_does_not_grow_with_row_count(user, folder):
    """`folder` is derived from the target, so a naive get_folder is one query per
    row -- and the inbox is not paginated (PAGE_SIZE 5000)."""
    notify_many(
        "expired_controls",
        [
            ([user], control, {"control_name": control.name})
            for control in controls(folder, 2)
        ],
    )
    few = len(
        queries(
            lambda: (
                NotificationReadSerializer(
                    list(Notification.objects.all()), many=True
                ).data
            )
        )
    )

    notify_many(
        "expired_controls",
        [
            ([user], control, {"control_name": control.name})
            for control in controls(folder, 10)
        ],
    )
    assert Notification.objects.count() == 12
    many = len(
        queries(
            lambda: (
                NotificationReadSerializer(
                    list(Notification.objects.all()), many=True
                ).data
            )
        )
    )

    assert many == few


def test_list_endpoint_does_not_grow_with_row_count(user, folder):
    factory = APIRequestFactory()

    def call():
        view = NotificationViewSet.as_view({"get": "list"})
        request = factory.get("/api/notifications/")
        force_authenticate(request, user=user)
        response = view(request)
        response.render()

    notify_many(
        "expired_controls",
        [
            ([user], control, {"control_name": control.name})
            for control in controls(folder, 2)
        ],
    )
    few = len(queries(call))

    notify_many(
        "expired_controls",
        [
            ([user], control, {"control_name": control.name})
            for control in controls(folder, 10)
        ],
    )
    assert len(queries(call)) == few


def test_sweep_overhead_is_constant(user, folder):
    """The channel matrix and the email->user resolution are read once per sweep,
    not once per object, so only the upsert scales."""
    # Built outside the measured block: creating an AppliedControl is itself several
    # queries, which would swamp the slope we are measuring.
    warmup = [([user.email], c, {}) for c in controls(folder, 1)]
    small = [
        ([user.email], control, {"control_name": control.name})
        for control in controls(folder, 2)
    ]
    large = [
        ([user.email], control, {"control_name": control.name})
        for control in controls(folder, 10)
    ]

    # Content types and the feature-flag cache are process-level, so a cold first call
    # would charge its lookups to whichever measurement ran first.
    notify_many("expired_controls", warmup)

    two = len(queries(lambda: notify_many("expired_controls", small)))
    ten = len(queries(lambda: notify_many("expired_controls", large)))

    # Two queries per object (the upsert's select and write), and a constant term that
    # does not move -- that constant is what used to be per object.
    per_object = (ten - two) / 8
    assert per_object == pytest.approx(2, abs=0.5)
    assert ten - 10 * per_object == pytest.approx(two - 2 * per_object, abs=0.5)
