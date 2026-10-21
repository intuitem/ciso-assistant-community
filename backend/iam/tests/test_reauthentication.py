"""Reauthenticating for a sensitive action (MFA, email changes) must use the
second factor when the account has one: a password alone is refused."""

import pytest
from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress
from allauth.core import context
from allauth.mfa.models import Authenticator
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from iam.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "a-strong-password-1"


@pytest.fixture
def user():
    user = User.objects.create_user(email="reauth@tests.local", password=PASSWORD)
    assert EmailAddress.objects.get_primary_email(user) == user.email
    return user


def reauthenticate(user, authentication_method="password"):
    request = RequestFactory().post("/")
    request.session = SessionStore()
    request.session["account_authentication_methods"] = [
        {"method": authentication_method, "at": 0}
    ]
    with context.request_context(request):
        return get_adapter().reauthenticate(user, PASSWORD)


def enable_totp(user):
    Authenticator.objects.create(
        user=user, type=Authenticator.Type.TOTP, data={"secret": "unused"}
    )


def test_password_is_enough_without_mfa(user):
    assert reauthenticate(user) is True


def test_password_is_refused_once_mfa_is_enabled(user):
    enable_totp(user)

    with pytest.raises(ValidationError) as exc:
        reauthenticate(user)
    assert exc.value.code == "mfa_required"


def test_password_is_enough_in_an_sso_session(user):
    # The IdP vouches for the second factor in an SSO session (MFAAdapter).
    enable_totp(user)

    assert reauthenticate(user, authentication_method="socialaccount") is True
