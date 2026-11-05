"""
Generic assignment notifications (AssignmentNotificationMixin): actors newly added to
an owner / assignee / author field get `object_assignment`, to a reviewers field
`object_review_assignment`. The model name is a paraglide key, localized in the
inbox by the frontend and in email by `_MODEL_LABELS`.

Tasks are queued with `transaction.on_commit`, and HUEY runs with
`immediate: False`, so they are swapped for in-process `.call_local()` runs.
"""

import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings

import automation.serializers  # noqa: F401  (imported so the mixin's subclasses load)
import crq.serializers  # noqa: F401
import doc_management.serializers  # noqa: F401
import ebios_rm.serializers  # noqa: F401
import metrology.serializers  # noqa: F401
import privacy.serializers  # noqa: F401
import resilience.serializers  # noqa: F401
import tprm.serializers  # noqa: F401
from core.email_utils import _MODEL_LABELS, _STATE_LABELS, paraglide_model_key
from core.models import FindingsAssessment
from core.serializers import (
    AssetWriteSerializer,
    AssignmentNotificationMixin,
    FindingsAssessmentWriteSerializer,
)
from iam.models import Folder, User
from notifications.registry import NOTIFICATION_REGISTRY

pytestmark = pytest.mark.django_db


def _wired_serializers():
    found, todo = [], list(AssignmentNotificationMixin.__subclasses__())
    while todo:
        cls = todo.pop()
        todo.extend(cls.__subclasses__())
        if cls.assignment_notifications:
            found.append(cls)
    return found


def test_every_wired_model_has_a_label_and_m2m_fields():
    wired = _wired_serializers()
    assert len(wired) >= 19
    for cls in wired:
        model = cls.Meta.model
        assert paraglide_model_key(model) in _MODEL_LABELS["en"], model
        for field, notification_type in cls.assignment_notifications.items():
            assert model._meta.get_field(field).many_to_many, (model, field)
            assert notification_type in NOTIFICATION_REGISTRY, notification_type


@pytest.mark.parametrize("locale", ["en", "fr", "de", "nl"])
def test_email_labels_match_the_paraglide_catalog(locale):
    path = Path(settings.BASE_DIR).parent / "frontend" / "messages" / f"{locale}.json"
    if not path.exists():
        pytest.skip("frontend messages not present in this checkout")
    catalog = json.loads(path.read_text())
    for labels in (_MODEL_LABELS, _STATE_LABELS):
        assert {k: catalog.get(k) for k in labels[locale]} == labels[locale]


@pytest.fixture
def folder(db):
    return Folder.objects.create(
        name="Assignment test domain", content_type=Folder.ContentType.DOMAIN
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

    task = tasks.send_object_assignment_notification
    with (
        patch(
            "core.tasks.send_object_assignment_notification",
            side_effect=lambda *a: task.call_local(*a),
        ),
        patch("core.tasks.check_email_configuration", return_value=True),
        patch("core.tasks.notify") as notify,
        patch("core.tasks.send_notification_email") as send_email,
        django_capture_on_commit_callbacks(execute=True),
    ):
        yield notify, send_email


def _save(serializer_class, data, instance=None):
    serializer = serializer_class(instance, data=data, partial=bool(instance))
    assert serializer.is_valid(), serializer.errors
    return serializer.save()


def _actors(*users):
    return [str(u.actor.id) for u in users]


def _asset(folder, owners):
    return _save(
        AssetWriteSerializer,
        {"name": "Payroll DB", "folder": str(folder.id), "owner": _actors(*owners)},
    )


def test_create_notifies_the_owners(folder, alice, django_capture_on_commit_callbacks):
    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        asset = _asset(folder, [alice])

    notification_type, recipients, target, context = notify.call_args.args
    assert notification_type == "object_assignment"
    assert recipients == [alice.email]
    assert target == asset
    assert context == {"object_name": "Payroll DB", "object_type_key": "asset"}
    assert send_email.call_args.args[2] == alice.email


def test_update_notifies_only_the_new_owner(
    folder, alice, bob, django_capture_on_commit_callbacks
):
    asset = _asset(folder, [alice])
    with _producer(django_capture_on_commit_callbacks) as (notify, _send_email):
        _save(AssetWriteSerializer, {"owner": _actors(alice, bob)}, asset)

    notify.assert_called_once()
    assert notify.call_args.args[1] == [bob.email]


def test_unchanged_owners_send_nothing(
    folder, alice, django_capture_on_commit_callbacks
):
    asset = _asset(folder, [alice])
    with _producer(django_capture_on_commit_callbacks) as (notify, _send_email):
        _save(AssetWriteSerializer, {"name": "Payroll DB v2"}, asset)

    notify.assert_not_called()


def test_an_owner_removed_before_the_task_runs_is_skipped(
    folder, alice, bob, django_capture_on_commit_callbacks
):
    from core import tasks

    task = tasks.send_object_assignment_notification
    with (
        patch(
            "core.tasks.send_object_assignment_notification",
            side_effect=lambda *a: task.call_local(*a),
        ),
        patch("core.tasks.check_email_configuration", return_value=True),
        patch("core.tasks.notify") as notify,
        patch("core.tasks.send_notification_email"),
    ):
        # Queue the task, change the owners, and only then let it run.
        with django_capture_on_commit_callbacks() as callbacks:
            asset = _asset(folder, [alice, bob])
        asset.owner.remove(bob.actor)
        for callback in callbacks:
            callback()

    assert notify.call_args.args[1] == [alice.email]


def test_reviewers_get_the_review_type(
    folder, alice, bob, django_capture_on_commit_callbacks
):
    with _producer(django_capture_on_commit_callbacks) as (notify, _send_email):
        binder = _save(
            FindingsAssessmentWriteSerializer,
            {
                "name": "Pentest Q3",
                "folder": str(folder.id),
                "authors": _actors(alice),
                "reviewers": _actors(bob),
            },
        )

    calls = {c.args[0]: c.args for c in notify.call_args_list}
    assert calls["object_assignment"][1] == [alice.email]
    assert calls["object_review_assignment"][1] == [bob.email]
    assert calls["object_review_assignment"][2] == binder
    assert isinstance(binder, FindingsAssessment)


@pytest.mark.parametrize(
    "locale,expected",
    [("fr", "Actif 'Payroll DB'"), ("nl", "Aan u toegewezen: Middel 'Payroll DB'")],
)
def test_email_names_the_model_in_the_recipient_language(
    folder, alice, locale, expected, django_capture_on_commit_callbacks
):
    with (
        patch("core.email_utils.get_email_preferences", return_value=(locale, "auto")),
        _producer(django_capture_on_commit_callbacks) as (_notify, send_email),
    ):
        _asset(folder, [alice])

    assert expected in send_email.call_args.args[0]
