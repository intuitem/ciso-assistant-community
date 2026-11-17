"""Logins refused by the failed-login rate limit are logged squashed
(iam.login_refusals), through the headless endpoint the frontend uses."""

import json

import pytest
from django.core.cache import cache
from django.test import Client, override_settings

from ciso_assistant import settings as project_settings
from iam import login_refusals

pytestmark = pytest.mark.django_db

LOGIN_URL = "/api/_allauth/app/v1/auth/login"


@pytest.fixture(autouse=True)
def fresh_limits():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def lines(monkeypatch):
    recorded = []

    class Recorder:
        def warning(self, event, **fields):
            recorded.append(fields)

    monkeypatch.setattr(login_refusals, "logger", Recorder())
    return recorded


def login(email, ip):
    return Client().post(
        LOGIN_URL,
        data=json.dumps({"email": email, "password": "wrong"}),
        content_type="application/json",
        HTTP_X_FORWARDED_FOR=ip,
    )


def test_a_spray_from_one_ip_is_squashed(lines):
    # 10 failures pass; the next 20 attempts, each with a new email, are
    # refused by the per-IP rule.
    for i in range(30):
        login(f"user{i}@tests.local", "203.0.113.1")

    assert lines == [
        {"remote_addr": "203.0.113.1", "refused": count} for count in (2, 4, 8, 16)
    ]


def test_many_ips_trying_one_email_are_squashed(lines):
    # 5 failures lock the email; the next 15 attempts, each from a new IP
    # address, are refused by the per-email rule.
    for i in range(20):
        login("victim@tests.local", f"198.51.100.{i}")

    assert lines == [
        {"username": "victim@tests.local", "refused": count} for count in (2, 4, 8)
    ]


def test_a_recap_is_logged_once_its_delay_has_passed(lines, monkeypatch):
    monkeypatch.setattr(login_refusals, "RECAP_SECONDS", 0)  # always due

    for i in range(15):
        login(f"user{i}@tests.local", "203.0.113.2")

    assert [line["refused"] for line in lines] == [2, 3, 4, 5]


@override_settings(
    CACHES={
        "default": project_settings._memcached_cache("unix:/nonexistent/memcached.sock")
    }
)
def test_nothing_is_logged_while_the_cache_is_unavailable(lines):
    for _ in range(4):
        login_refusals.record_refused_login(None, {"email": "victim@tests.local"})

    assert lines == []
