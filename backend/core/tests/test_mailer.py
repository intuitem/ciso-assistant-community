"""core.mailer: ordered failover on connection failure only, and the
environment-to-MAILERS builder behind it."""

import pytest
from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.locmem import EmailBackend as LocmemBackend

from ciso_assistant.mailers import CONSOLE_BACKEND, SMTP_BACKEND, build_mailers
from core import mailer

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
HERE = "core.tests.test_mailer"


class RefusingBackend(BaseEmailBackend):
    """Cannot be opened: what a down SMTP server looks like to Django."""

    opened = 0

    def open(self):
        RefusingBackend.opened += 1
        raise ConnectionRefusedError("connection refused")

    def send_messages(self, email_messages):
        raise AssertionError("must never be asked to send")


class FailingAfterOpenBackend(LocmemBackend):
    """Opens fine, then the server rejects the message: no failover."""

    def send_messages(self, email_messages):
        raise RuntimeError("550 rejected after handover")


class SilentDropBackend(LocmemBackend):
    def send_messages(self, email_messages):
        return 0


@pytest.fixture(autouse=True)
def reset_counters():
    RefusingBackend.opened = 0


# --- configuration ---------------------------------------------------------


def test_nothing_configured_disables_mailing(settings):
    settings.MAILERS = {}
    settings.DEFAULT_FROM_EMAIL = None
    assert mailer.mailing_enabled() is False
    assert mailer.missing_configuration() == ["EMAIL_HOST", "DEFAULT_FROM_EMAIL"]


def test_sender_address_is_required(settings):
    settings.MAILERS = {"default": {"BACKEND": LOCMEM}}
    settings.DEFAULT_FROM_EMAIL = None
    assert mailer.mailing_enabled() is False
    assert mailer.missing_configuration() == ["DEFAULT_FROM_EMAIL"]


def test_configured_mailer_and_sender_enable_mailing(settings):
    settings.MAILERS = {"default": {"BACKEND": LOCMEM}}
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
    assert mailer.mailing_enabled() is True


def test_build_mailers_empty_environment():
    assert build_mailers({}) == {}


def test_build_mailers_primary_only():
    mailers = build_mailers(
        {
            "EMAIL_HOST": "smtp.example",
            "EMAIL_PORT": "587",
            "EMAIL_HOST_USER": "apikey",
            "EMAIL_HOST_PASSWORD": "secret",
            "EMAIL_USE_TLS": "true",
            "EMAIL_TIMEOUT": "9",
        }
    )
    assert list(mailers) == ["default"]
    assert mailers["default"] == {
        "BACKEND": SMTP_BACKEND,
        "OPTIONS": {
            "host": "smtp.example",
            "port": 587,
            "username": "apikey",
            "password": "secret",
            "use_tls": True,
            "use_ssl": False,
            "timeout": 9,
        },
    }


def test_build_mailers_primary_then_rescue_in_failover_order():
    mailers = build_mailers(
        {
            "EMAIL_HOST": "smtp.example",
            "EMAIL_HOST_RESCUE": "smtp2.example",
            "EMAIL_USE_SSL_RESCUE": "1",
        }
    )
    assert list(mailers) == ["default", "rescue"]
    assert mailers["rescue"]["OPTIONS"]["host"] == "smtp2.example"
    assert mailers["rescue"]["OPTIONS"]["use_ssl"] is True
    assert mailers["rescue"]["OPTIONS"]["port"] is None


def test_build_mailers_rescue_alone_becomes_the_default():
    # Today EMAIL_HOST_RESCUE alone enables mailing; keep that.
    mailers = build_mailers({"EMAIL_HOST_RESCUE": "smtp2.example"})
    assert list(mailers) == ["default"]
    assert mailers["default"]["OPTIONS"]["host"] == "smtp2.example"


def test_build_mailers_rejects_tls_and_ssl_together():
    with pytest.raises(
        ValueError, match="EMAIL_USE_TLS_RESCUE and EMAIL_USE_SSL_RESCUE"
    ):
        build_mailers(
            {
                "EMAIL_HOST_RESCUE": "smtp2.example",
                "EMAIL_USE_TLS_RESCUE": "yes",
                "EMAIL_USE_SSL_RESCUE": "yes",
            }
        )


def test_build_mailers_mail_debug_uses_console_only():
    mailers = build_mailers({"EMAIL_HOST": "smtp.example"}, mail_debug=True)
    assert mailers == {"default": {"BACKEND": CONSOLE_BACKEND}}


# --- sending and failover ---------------------------------------------------


def test_send_uses_the_first_mailer(settings):
    settings.MAILERS = {
        "default": {"BACKEND": LOCMEM},
        "rescue": {"BACKEND": f"{HERE}.RefusingBackend"},
    }
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
    mailer.send("S", "body", "a@tests.local")
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["a@tests.local"]
    assert mail.outbox[0].from_email == "ciso@tests.local"
    assert RefusingBackend.opened == 0


def test_send_html_body(settings):
    settings.MAILERS = {"default": {"BACKEND": LOCMEM}}
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
    mailer.send("S", "text", "a@tests.local", html_body="<p>hi</p>")
    assert mail.outbox[0].body == "<p>hi</p>"
    assert mail.outbox[0].content_subtype == "html"


def test_unreachable_first_mailer_fails_over_to_the_next(settings):
    settings.MAILERS = {
        "default": {"BACKEND": f"{HERE}.RefusingBackend"},
        "rescue": {"BACKEND": LOCMEM},
    }
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
    mailer.send("S", "body", "a@tests.local")
    assert RefusingBackend.opened == 1
    assert [m.to for m in mail.outbox] == [["a@tests.local"]]


def test_failure_after_handover_does_not_fail_over(settings):
    settings.MAILERS = {
        "default": {"BACKEND": f"{HERE}.FailingAfterOpenBackend"},
        "rescue": {"BACKEND": LOCMEM},
    }
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
    with pytest.raises(RuntimeError, match="550"):
        mailer.send("S", "body", "a@tests.local")
    assert mail.outbox == []


def test_every_mailer_unreachable_raises(settings):
    settings.MAILERS = {
        "default": {"BACKEND": f"{HERE}.RefusingBackend"},
        "rescue": {"BACKEND": f"{HERE}.RefusingBackend"},
    }
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
    with pytest.raises(mailer.NoMailerAvailable, match="default, rescue") as info:
        mailer.send("S", "body", "a@tests.local")
    assert isinstance(info.value.__cause__, ConnectionRefusedError)
    assert RefusingBackend.opened == 2


def test_no_mailer_configured_raises(settings):
    settings.MAILERS = {}
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
    with pytest.raises(mailer.NoMailerAvailable, match="EMAIL_HOST"):
        mailer.send("S", "body", "a@tests.local")


def test_zero_sent_is_a_failure(settings):
    settings.MAILERS = {"default": {"BACKEND": f"{HERE}.SilentDropBackend"}}
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
    with pytest.raises(RuntimeError, match="0 of 1"):
        mailer.send("S", "body", "a@tests.local")


def test_open_connection_batches_on_one_mailer(settings):
    settings.MAILERS = {
        "default": {"BACKEND": f"{HERE}.RefusingBackend"},
        "rescue": {"BACKEND": LOCMEM},
    }
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
    with mailer.open_connection() as connection:
        mailer.send("S", "body", "a@tests.local", connection=connection)
        mailer.send("S", "body", "b@tests.local", connection=connection)
    assert RefusingBackend.opened == 1
    assert [m.to[0] for m in mail.outbox] == ["a@tests.local", "b@tests.local"]
