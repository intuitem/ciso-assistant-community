"""Failed logins are recorded (iam.signals): a log line and a LOGIN_FAILED
audit entry. prune_auditlog caps them apart from other entries: they need no
account, so a flood of them must not push those out."""

import json
from datetime import timedelta
from io import StringIO

import pytest
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from global_settings.models import GlobalSettings
from iam.models import User
from iam.signals import LOGIN_FAILED_ACTION

pytestmark = pytest.mark.django_db

LOGIN_URL = "/api/_allauth/app/v1/auth/login"
EMAIL = "failed-login@tests.local"
PASSWORD = "Correct-Horse-Battery-9!"


@pytest.fixture(autouse=True)
def fresh_limits():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user():
    user = User.objects.create_user(email=EMAIL, password=PASSWORD)
    user.is_active = True
    user.save()
    return user


def login(email, password):
    return Client().post(
        LOGIN_URL,
        data=json.dumps({"email": email, "password": password}),
        content_type="application/json",
        HTTP_X_FORWARDED_FOR="203.0.113.7",
    )


def failed_logins():
    return LogEntry.objects.filter(action=LOGIN_FAILED_ACTION)


def test_a_wrong_password_is_recorded(user):
    login(EMAIL, "wrong")

    entry = failed_logins().get()
    assert entry.object_repr == EMAIL
    assert entry.remote_addr == "203.0.113.7"
    assert entry.additional_data == {"username": EMAIL}


def test_an_unknown_email_is_recorded():
    login("nobody@tests.local", "wrong")

    assert failed_logins().get().object_repr == "nobody@tests.local"


def test_a_password_refused_by_forced_sso_is_recorded(user):
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.SSO,
        defaults={"value": {"is_enabled": True, "force_sso": True}},
    )

    login(EMAIL, PASSWORD)

    assert failed_logins().count() == 1


def test_a_successful_login_is_not_recorded(user):
    assert login(EMAIL, PASSWORD).status_code == 200

    assert not failed_logins().exists()


def test_failed_logins_cannot_push_other_entries_out(settings):
    others = LogEntry.objects.exclude(action=LOGIN_FAILED_ACTION)
    content_type = ContentType.objects.get_for_model(User)
    LogEntry.objects.bulk_create(
        LogEntry(
            content_type=content_type,
            object_repr=f"change {i}",
            action=LogEntry.Action.UPDATE,
            timestamp=timezone.now() - timedelta(minutes=1),
        )
        for i in range(10)
    )
    # Each kind of entry keeps its newest AUDITLOG_MAX_RECORDS + 1000.
    cap = others.count()
    settings.AUDITLOG_MAX_RECORDS = cap - 1000
    LogEntry.objects.bulk_create(
        LogEntry(
            content_type=content_type, object_repr="flood", action=LOGIN_FAILED_ACTION
        )
        for _ in range(cap + 50)
    )

    call_command("prune_auditlog", stdout=StringIO())

    assert others.count() == cap
    assert others.filter(object_repr__startswith="change ").count() == 10
    assert failed_logins().count() == cap
