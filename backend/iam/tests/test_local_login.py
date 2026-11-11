"""Who may log in with a password (User.is_local), enforced by
iam.auth_backends.LocalLoginBackend under allauth's own authenticate, through
the headless endpoint the frontend uses.

Forcing SSO does not make existing passwords unusable (User.save does, the
next time the user is saved), so the rule must hold at login."""

import json

import pytest
from allauth.account.adapter import get_adapter
from django.contrib.auth import get_user
from django.contrib.auth.hashers import make_password
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from django.test import Client, RequestFactory

from global_settings.models import GlobalSettings
from iam.models import User

pytestmark = pytest.mark.django_db

LOGIN_URL = "/api/_allauth/app/v1/auth/login"
EMAIL = "local-login@tests.local"
PASSWORD = "Correct-Horse-Battery-9!"


@pytest.fixture(autouse=True)
def fresh_limits():
    cache.clear()
    yield
    cache.clear()


def make_user(**fields):
    """A user whose password is usable whatever the fields say: update()
    skips User.save, which would make it unusable for a non-local user."""
    user = User.objects.create_user(email=EMAIL, password=PASSWORD)
    fields = {"is_active": True, "password": make_password(PASSWORD), **fields}
    User.objects.filter(pk=user.pk).update(**fields)
    return User.objects.get(pk=user.pk)


def force_sso():
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.SSO,
        defaults={"value": {"is_enabled": True, "force_sso": True}},
    )


def login(password, ip="203.0.113.7"):
    return Client().post(
        LOGIN_URL,
        data=json.dumps({"email": EMAIL, "password": password}),
        content_type="application/json",
        HTTP_X_FORWARDED_FOR=ip,
    )


def error_codes(response):
    return [error["code"] for error in response.json().get("errors", [])]


def test_local_user_logs_in():
    make_user()

    assert login(PASSWORD).status_code == 200


def test_inactive_user_is_refused():
    make_user(is_active=False)

    assert error_codes(login(PASSWORD)) == ["email_password_mismatch"]


def test_scim_user_with_a_leftover_password_is_refused():
    make_user(is_scim_managed=True)

    assert error_codes(login(PASSWORD)) == ["email_password_mismatch"]


def test_forcing_sso_refuses_a_still_usable_password():
    make_user()
    force_sso()

    assert error_codes(login(PASSWORD)) == ["email_password_mismatch"]


def test_keep_local_login_survives_forced_sso():
    make_user(keep_local_login=True)
    force_sso()

    assert login(PASSWORD).status_code == 200


def test_a_refused_right_password_counts_as_a_failure():
    """Otherwise the attempt after it would tell whether the guess was right:
    the per-email lockout would or would not trigger."""
    make_user()
    force_sso()
    for i in range(4):
        login("wrong", ip=f"203.0.113.{i}")

    assert error_codes(login(PASSWORD, ip="203.0.113.50")) == [
        "email_password_mismatch"
    ]
    assert error_codes(login("wrong", ip="203.0.113.51")) == ["too_many_login_attempts"]


def test_sso_user_keeps_its_session():
    """allauth logs SSO users in through the first backend: its get_user must
    not apply the local-login rule."""
    user = make_user(is_jit_provisioned=True)
    assert not user.is_local
    request = RequestFactory().get("/")
    SessionMiddleware(lambda request: None).process_request(request)

    get_adapter(request).login(request, user)

    assert get_user(request) == user
