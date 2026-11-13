"""EE displays the failed logins that both editions record (iam.signals): one
LOGIN_FAILED entry per failed login, labelled for the audit log page."""

import json

import pytest
from auditlog.models import LogEntry
from django.core.cache import cache
from django.test import Client

from enterprise_core.models import LogEntryAction

pytestmark = pytest.mark.django_db


def test_a_failed_login_is_recorded_once_and_labelled(app_config):
    cache.clear()

    Client().post(
        "/api/_allauth/app/v1/auth/login",
        data=json.dumps({"email": "ee-nobody@tests.local", "password": "wrong"}),
        content_type="application/json",
        HTTP_X_FORWARDED_FOR="203.0.113.7",
    )

    entry = LogEntry.objects.get(action=LogEntryAction.LOGIN_FAILED)
    assert entry.object_repr == "ee-nobody@tests.local"
    assert entry.remote_addr == "203.0.113.7"
    assert LogEntryAction(entry.action).to_string() == "loginFailed"
