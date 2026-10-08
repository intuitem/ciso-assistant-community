"""core.mailer.send_test and the send_test_email management command."""

from io import StringIO

import pytest
from django.core import mail
from django.core.management import CommandError, call_command

from core import mailer
from core.tests.test_mailer import FailingAfterOpenBackend, RefusingBackend  # noqa: F401

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
FAKES = "core.tests.test_mailer"


def configure(settings, **mailers):
    settings.MAILERS = {
        alias: {"BACKEND": backend} for alias, backend in mailers.items()
    }
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"


# --- the service entry point --------------------------------------------------


def test_send_test_reports_the_mailer_that_delivered(settings):
    configure(settings, default=LOCMEM)
    result = mailer.send_test("admin@tests.local")
    assert result.ok is True
    assert (result.mailer, result.backend) == ("default", "EmailBackend")
    assert result.skipped == []
    assert "through mailer default" in result.summary
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["admin@tests.local"]
    assert mail.outbox[0].subject == "CISO Assistant test email"
    assert "mailer 'default'" in mail.outbox[0].body


def test_send_test_reports_skipped_mailers(settings):
    configure(settings, default=f"{FAKES}.RefusingBackend", rescue=LOCMEM)
    result = mailer.send_test("admin@tests.local")
    assert result.ok is True
    assert result.mailer == "rescue"
    assert [alias for alias, _ in result.skipped] == ["default"]
    assert "connection refused" in result.skipped[0][1]


def test_send_test_does_not_raise_when_nothing_is_configured(settings):
    settings.MAILERS = {}
    settings.DEFAULT_FROM_EMAIL = None
    result = mailer.send_test("admin@tests.local")
    assert result.ok is False
    assert "EMAIL_HOST" in result.error and "DEFAULT_FROM_EMAIL" in result.error
    assert mail.outbox == []


def test_send_test_reports_a_delivery_failure(settings):
    configure(settings, default=f"{FAKES}.FailingAfterOpenBackend", rescue=LOCMEM)
    result = mailer.send_test("admin@tests.local")
    assert result.ok is False
    assert "550" in result.error
    assert mail.outbox == []


def test_send_test_reports_every_mailer_unreachable(settings):
    configure(
        settings,
        default=f"{FAKES}.RefusingBackend",
        rescue=f"{FAKES}.RefusingBackend",
    )
    result = mailer.send_test("admin@tests.local")
    assert result.ok is False
    assert "no mailer reachable" in result.error
    assert [alias for alias, _ in result.skipped] == ["default", "rescue"]


# --- the management command ---------------------------------------------------


def test_command_prints_configuration_and_success(settings):
    configure(settings, default=LOCMEM)
    out = StringIO()
    call_command("send_test_email", "admin@tests.local", stdout=out)
    text = out.getvalue()
    assert "mailer default:" in text
    assert "sender: ciso@tests.local" in text
    assert "test email sent to admin@tests.local through mailer default" in text
    assert len(mail.outbox) == 1


def test_command_shows_skipped_mailers(settings):
    configure(settings, default=f"{FAKES}.RefusingBackend", rescue=LOCMEM)
    out = StringIO()
    call_command("send_test_email", "admin@tests.local", stdout=out)
    assert "mailer default skipped: connection refused" in out.getvalue()
    assert "through mailer rescue" in out.getvalue()


def test_command_fails_with_the_reason(settings):
    settings.MAILERS = {}
    settings.DEFAULT_FROM_EMAIL = None
    with pytest.raises(CommandError, match="not configured"):
        call_command("send_test_email", "admin@tests.local", stdout=StringIO())
