"""The callers whose "is mail configured?" gate moved to core.mailer must
behave as before: password reset and user creation."""

import pytest
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient

from iam.models import User

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"

pytestmark = pytest.mark.django_db


def configure_mail(settings):
    settings.MAILERS = {"default": {"BACKEND": LOCMEM}}
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"


def disable_mail(settings):
    settings.MAILERS = {}


# --- password reset ---------------------------------------------------------


def test_password_reset_sends_when_configured(settings):
    configure_mail(settings)
    User.objects.create_user(email="jane@tests.local", password="pw-not-mailed")
    mail.outbox.clear()

    response = APIClient().post(
        reverse("password-reset"), {"email": "jane@tests.local"}, format="json"
    )

    assert response.status_code == 202
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["jane@tests.local"]
    assert "Password Reset" in mail.outbox[0].subject


def test_password_reset_stays_neutral_for_unknown_address(settings):
    configure_mail(settings)

    response = APIClient().post(
        reverse("password-reset"), {"email": "nobody@tests.local"}, format="json"
    )

    assert response.status_code == 202
    assert mail.outbox == []


def test_password_reset_reports_missing_mailer(settings):
    disable_mail(settings)
    User.objects.create_user(email="jane@tests.local", password="pw")

    response = APIClient().post(
        reverse("password-reset"), {"email": "jane@tests.local"}, format="json"
    )

    assert response.status_code == 500
    assert "not configured" in response.json()["error"]
    assert mail.outbox == []


# --- user creation ----------------------------------------------------------


def test_creating_a_user_without_password_sends_the_welcome_mail(settings):
    configure_mail(settings)

    user = User.objects.create_user(email="new@tests.local")

    assert user.pk
    assert [m.to for m in mail.outbox] == [["new@tests.local"]]


def test_creating_a_user_without_a_mailer_sends_nothing_and_succeeds(settings):
    disable_mail(settings)

    user = User.objects.create_user(email="new@tests.local")

    assert user.pk
    assert mail.outbox == []


def test_creating_a_superuser_with_a_password_sends_nothing(settings):
    configure_mail(settings)

    user = User.objects.create_superuser(email="root@tests.local", password="pw")

    assert user.is_superuser
    assert mail.outbox == []
