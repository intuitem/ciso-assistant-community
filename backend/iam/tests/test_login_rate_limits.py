"""Login brute-force limits (allauth's ACCOUNT_RATE_LIMITS) through the
headless endpoint the frontend uses.

AccountAdapter keeps allauth's authenticate, which consumes the "login_failed"
limit and rolls it back on success. The override that used to replace it
skipped both, so failed logins were never limited. Per-IP limits key on the
client IP resolved from X-Forwarded-For
(core.custom_middleware.resolve_client_ip). LOGIN_RATE_LIMIT and
LOGIN_FAILED_RATE_LIMIT set the two login limits."""

import json

import pytest
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, override_settings

from ciso_assistant import settings as project_settings
from iam.models import User

pytestmark = pytest.mark.django_db

LOGIN_URL = "/api/_allauth/app/v1/auth/login"
EMAIL = "victim@tests.local"
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


def login(email, password, xff):
    return Client().post(
        LOGIN_URL,
        data=json.dumps({"email": email, "password": password}),
        content_type="application/json",
        REMOTE_ADDR="10.0.0.9",
        HTTP_X_FORWARDED_FOR=xff,
    )


def error_codes(response):
    return [error["code"] for error in response.json().get("errors", [])]


def test_correct_password_logs_in(user):
    assert login(EMAIL, PASSWORD, "203.0.113.1").status_code == 200


def test_five_failures_lock_the_account_even_for_the_right_password(user):
    for i in range(5):
        response = login(EMAIL, "wrong", f"203.0.113.{i}")
        assert error_codes(response) == ["email_password_mismatch"]

    response = login(EMAIL, PASSWORD, "198.51.100.1")

    assert response.status_code == 400
    # A non-field error: the login page shows it without a param.
    assert response.json()["errors"] == [
        {
            "code": "too_many_login_attempts",
            "message": response.json()["errors"][0]["message"],
        }
    ]


def test_failures_per_ip_follow_the_last_forwarded_for_entry(user):
    for i in range(10):
        login(f"nobody{i}@tests.local", "wrong", "203.0.113.5")

    blocked = login("other@tests.local", "wrong", "203.0.113.5")
    other_client = login("other@tests.local", "wrong", "203.0.113.5, 198.51.100.9")
    spoofed_prefix = login("other@tests.local", "wrong", "198.51.100.9, 203.0.113.5")

    assert error_codes(blocked) == ["too_many_login_attempts"]
    assert error_codes(other_client) == ["email_password_mismatch"]
    assert error_codes(spoofed_prefix) == ["too_many_login_attempts"]


def test_successful_logins_are_not_counted_as_failures(user):
    for _ in range(12):  # more than the 10 failures/min/IP
        assert login(EMAIL, PASSWORD, "203.0.113.8").status_code == 200

    response = login(EMAIL, "wrong", "203.0.113.8")

    assert error_codes(response) == ["email_password_mismatch"]


def test_too_many_attempts_from_one_ip_answer_a_bare_429(user):
    for _ in range(30):
        login(EMAIL, PASSWORD, "203.0.113.9")

    response = login(EMAIL, PASSWORD, "203.0.113.9")

    assert response.status_code == 429
    # No "errors": the login page maps the bare 429 itself.
    assert "errors" not in response.json()


@pytest.fixture
def login_rate_env(monkeypatch):
    monkeypatch.delenv("LOGIN_RATE_LIMIT", raising=False)
    monkeypatch.delenv("LOGIN_FAILED_RATE_LIMIT", raising=False)
    return monkeypatch


def test_default_limits_are_allauths(login_rate_env):
    assert project_settings._login_rate_limits() == {
        "login": "30/m/ip",
        "login_failed": "10/m/ip,5/5m/key",
    }


@pytest.mark.parametrize(
    "variable, action, value, expected",
    [
        # No per-email lockout:
        ("LOGIN_FAILED_RATE_LIMIT", "login_failed", "10/m/ip", "10/m/ip"),
        (
            "LOGIN_FAILED_RATE_LIMIT",
            "login_failed",
            " 20/m, 3/1h/key ",
            "20/m, 3/1h/key",
        ),
        ("LOGIN_FAILED_RATE_LIMIT", "login_failed", "", ""),  # off
        ("LOGIN_RATE_LIMIT", "login", "60/1.5m/ip", "60/1.5m/ip"),
        ("LOGIN_RATE_LIMIT", "login", "  ", ""),  # off
    ],
)
def test_limits_are_read_from_the_environment(
    login_rate_env, variable, action, value, expected
):
    login_rate_env.setenv(variable, value)

    assert project_settings._login_rate_limits()[action] == expected


@pytest.mark.parametrize(
    "variable, value",
    [
        ("LOGIN_FAILED_RATE_LIMIT", "5/5min/key"),  # unknown period unit
        ("LOGIN_FAILED_RATE_LIMIT", "10/m/ip,"),  # empty rule
        ("LOGIN_FAILED_RATE_LIMIT", "0/m/ip"),  # would block every login
        ("LOGIN_FAILED_RATE_LIMIT", "5/m/user"),  # nobody is logged in yet
        ("LOGIN_RATE_LIMIT", "5/m/key"),  # allauth passes no key for "login"
        ("LOGIN_RATE_LIMIT", "ten/m"),
    ],
)
def test_malformed_limits_stop_the_backend(login_rate_env, variable, value):
    login_rate_env.setenv(variable, value)

    with pytest.raises(ImproperlyConfigured, match=variable):
        project_settings._login_rate_limits()


@override_settings(ACCOUNT_RATE_LIMITS={"login_failed": "10/m/ip"})
def test_without_a_key_rule_failures_do_not_lock_the_account(user):
    for i in range(6):
        login(EMAIL, "wrong", f"203.0.113.{i}")

    assert login(EMAIL, PASSWORD, "198.51.100.1").status_code == 200


@override_settings(ACCOUNT_RATE_LIMITS={"login": "", "login_failed": ""})
def test_empty_limits_turn_login_limiting_off(user):
    for _ in range(31):
        response = login(EMAIL, "wrong", "203.0.113.9")
        assert error_codes(response) == ["email_password_mismatch"]

    assert login(EMAIL, PASSWORD, "203.0.113.9").status_code == 200
