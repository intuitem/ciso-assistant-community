"""core.mailer: ordered failover on connection failure only, and the
environment-to-MAILERS builder behind it."""

import smtplib
import socket
import ssl

import pytest
from django.core import mail
from django.core.mail import mailers
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.locmem import EmailBackend as LocmemBackend

from ciso_assistant.mailers import CONSOLE_BACKEND, SMTP_BACKEND, build_mailers
from core import mailer
from core.email_backend import EmailBackend

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


class UncleanCloseBackend(LocmemBackend):
    """Delivers, then QUIT fails: cleanup noise, not a delivery failure."""

    def close(self):
        raise RuntimeError("421 closing transmission channel")


class LoginRefusedSMTP:
    """Accepts the TCP connection, then rejects the password."""

    instances: list = []

    def __init__(self, host, port, local_hostname=None, timeout=None):
        self.closed = False
        LoginRefusedSMTP.instances.append(self)

    def login(self, user, password):
        raise smtplib.SMTPAuthenticationError(535, b"5.7.8 bad credentials")

    def quit(self):
        self.closed = True

    def close(self):
        self.closed = True


class LoginRefusedBackend(EmailBackend):
    connection_class = LoginRefusedSMTP


@pytest.fixture(autouse=True)
def reset_counters():
    RefusingBackend.opened = 0
    LoginRefusedSMTP.instances = []


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


def test_build_mailers_rejects_non_numeric_port():
    with pytest.raises(ValueError, match="EMAIL_PORT_RESCUE must be a number"):
        build_mailers(
            {"EMAIL_HOST_RESCUE": "smtp2.example", "EMAIL_PORT_RESCUE": "smtp"}
        )


@pytest.mark.parametrize(
    "flags, built, connected",
    [
        # Before MAILERS an unset port reached smtplib as 0, i.e. 25, even
        # with STARTTLS; Django's mailers would otherwise pick 587.
        ({"EMAIL_USE_TLS": "True"}, 25, 25),
        ({}, 25, 25),
        ({"EMAIL_USE_SSL": "True"}, None, 465),
    ],
)
def test_unset_port_keeps_the_pre_mailers_default(settings, flags, built, connected):
    settings.MAILERS = build_mailers({"EMAIL_HOST": "smtp.example", **flags})
    assert settings.MAILERS["default"]["OPTIONS"]["port"] == built
    assert mailers["default"].port == connected


def test_build_mailers_reads_the_client_certificate(settings):
    settings.MAILERS = build_mailers(
        {
            "EMAIL_HOST": "smtp.example",
            "EMAIL_SSL_CERTFILE": "/certs/client.pem",
            "EMAIL_SSL_KEYFILE": "/certs/client.key",
            "EMAIL_HOST_RESCUE": "smtp2.example",
            "EMAIL_SSL_CERTFILE_RESCUE": "/certs/rescue.pem",
        }
    )
    primary = mailers["default"]
    rescue = mailers["rescue"]
    assert (primary.ssl_certfile, primary.ssl_keyfile) == (
        "/certs/client.pem",
        "/certs/client.key",
    )
    assert (rescue.ssl_certfile, rescue.ssl_keyfile) == ("/certs/rescue.pem", None)


def test_build_mailers_without_client_certificate_emits_no_cert_options():
    options = build_mailers({"EMAIL_HOST": "smtp.example"})["default"]["OPTIONS"]
    assert "ssl_certfile" not in options
    assert "ssl_keyfile" not in options


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


def test_rejected_login_releases_the_socket_before_failing_over(settings):
    # Django keeps a half-open connection on the backend when login fails;
    # failover must close it rather than leave it to the garbage collector.
    settings.MAILERS = {
        "default": {
            "BACKEND": f"{HERE}.LoginRefusedBackend",
            "OPTIONS": {
                "host": "smtp.example",
                "port": 25,
                "username": "apikey",
                "password": "wrong",
            },
        },
        "rescue": {"BACKEND": LOCMEM},
    }
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
    mailer.send("S", "body", "a@tests.local")
    assert [m.to for m in mail.outbox] == [["a@tests.local"]]
    assert [smtp.closed for smtp in LoginRefusedSMTP.instances] == [True]


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


def test_unclean_close_does_not_fail_a_delivered_message(settings):
    settings.MAILERS = {"default": {"BACKEND": f"{HERE}.UncleanCloseBackend"}}
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
    mailer.send("S", "body", "a@tests.local")
    assert len(mail.outbox) == 1


def test_unclean_close_does_not_mask_the_callers_error(settings):
    settings.MAILERS = {"default": {"BACKEND": f"{HERE}.UncleanCloseBackend"}}
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
    with pytest.raises(ValueError, match="from the caller"):
        with mailer.open_connection():
            raise ValueError("from the caller")


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


@pytest.mark.parametrize(
    "error, expected",
    [
        (
            smtplib.SMTPAuthenticationError(
                535, b"5.7.8 Username and Password not accepted"
            ),
            "server replied 535 5.7.8 Username and Password not accepted",
        ),
        (
            smtplib.SMTPRecipientsRefused({"a@tests.local": (550, b"no such user")}),
            "server refused the recipient (550)",
        ),
        (
            smtplib.SMTPServerDisconnected("Connection unexpectedly closed"),
            "server closed the connection",
        ),
        (
            ssl.SSLError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] ..."),
            "TLS handshake failed",
        ),
        (
            socket.gaierror(8, "nodename nor servname provided"),
            "host name could not be resolved",
        ),
        (TimeoutError("timed out"), "connection timed out"),
        (ConnectionRefusedError(61, "Connection refused"), "connection refused"),
        (OSError(65, "No route to host"), "No route to host"),
        # Our own exceptions carry a message written for the reader.
        (
            mailer.NoMailerAvailable("no mailer reachable, tried default"),
            "no mailer reachable, tried default",
        ),
        (
            RuntimeError("email backend reported 0 of 1 messages sent"),
            "email backend reported 0 of 1 messages sent",
        ),
    ],
)
def test_describe_error_speaks_for_the_network_and_the_server(error, expected):
    assert mailer.describe_error(error) == expected
