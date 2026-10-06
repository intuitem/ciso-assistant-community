"""Backwards compatibility of the EMAIL_* environment variables.

Running deployments configure mail through EMAIL_HOST and friends and must
keep working unchanged after the move to MAILERS. These tests pin the seams
the unit tests of the builder do not reach: Django's SMTP backend accepting
every option we emit, the real settings module reading the environment, and a
real connection refusal taking the failover path.
"""

import json
import os
import socket
import subprocess
import sys
import warnings
from pathlib import Path

import pytest
from django.core import mail
from django.core.mail import mailers

from ciso_assistant.mailers import build_mailers
from core import mailer
from core.email_backend import EmailBackend

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
BACKEND_DIR = Path(__file__).resolve().parents[2]

ENV = {
    "EMAIL_HOST": "smtp.example",
    "EMAIL_PORT": "587",
    "EMAIL_HOST_USER": "apikey",
    "EMAIL_HOST_PASSWORD": "secret",
    "EMAIL_USE_TLS": "True",
    "EMAIL_TIMEOUT": "7",
    "EMAIL_HOST_RESCUE": "smtp2.example",
    "EMAIL_PORT_RESCUE": "465",
    "EMAIL_HOST_USER_RESCUE": "rescue",
    "EMAIL_HOST_PASSWORD_RESCUE": "rescue-secret",
    "EMAIL_USE_SSL_RESCUE": "True",
}


# --- every emitted option is one Django's SMTP backend accepts ------------


def test_options_fit_django_smtp_backend(settings):
    settings.MAILERS = build_mailers(ENV)
    with warnings.catch_warnings():
        # An unknown OPTIONS key is dropped by Django with a deprecation
        # warning; make that a hard failure.
        warnings.simplefilter("error")
        primary = mailers["default"]
        rescue = mailers["rescue"]

    assert isinstance(primary, EmailBackend)
    assert (primary.host, primary.port) == ("smtp.example", 587)
    assert (primary.username, primary.password) == ("apikey", "secret")
    assert (primary.use_tls, primary.use_ssl) == (True, False)
    assert primary.timeout == 7

    assert isinstance(rescue, EmailBackend)
    assert (rescue.host, rescue.port) == ("smtp2.example", 465)
    assert (rescue.username, rescue.password) == ("rescue", "rescue-secret")
    assert (rescue.use_tls, rescue.use_ssl) == (False, True)
    # EMAIL_TIMEOUT has always applied to both servers.
    assert rescue.timeout == 7


def test_empty_user_and_password_mean_no_login():
    mailers_config = build_mailers(
        {"EMAIL_HOST": "smtp.example", "EMAIL_HOST_USER": "", "EMAIL_HOST_PASSWORD": ""}
    )
    options = mailers_config["default"]["OPTIONS"]
    assert options["username"] is None
    assert options["password"] is None


@pytest.mark.parametrize("value", ["True", "true", "TRUE", "1", "yes", "Yes"])
def test_flag_spellings_that_enable(value):
    mailers_config = build_mailers(
        {"EMAIL_HOST": "smtp.example", "EMAIL_USE_TLS": value}
    )
    assert mailers_config["default"]["OPTIONS"]["use_tls"] is True


@pytest.mark.parametrize("value", ["False", "false", "0", "no", "", "anything"])
def test_flag_spellings_that_disable(value):
    mailers_config = build_mailers(
        {"EMAIL_HOST": "smtp.example", "EMAIL_USE_TLS": value}
    )
    assert mailers_config["default"]["OPTIONS"]["use_tls"] is False


# --- a real refused SMTP connection fails over --------------------------------


def _closed_local_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_refused_smtp_connection_fails_over_to_rescue(settings):
    port = _closed_local_port()
    settings.MAILERS = {
        "default": {
            "BACKEND": "core.email_backend.EmailBackend",
            "OPTIONS": {"host": "127.0.0.1", "port": port, "timeout": 2},
        },
        "rescue": {"BACKEND": LOCMEM},
    }
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
    mailer.send("S", "body", "a@tests.local")
    assert [m.to for m in mail.outbox] == [["a@tests.local"]]


def test_refused_smtp_connection_with_no_rescue_raises(settings):
    port = _closed_local_port()
    settings.MAILERS = {
        "default": {
            "BACKEND": "core.email_backend.EmailBackend",
            "OPTIONS": {"host": "127.0.0.1", "port": port, "timeout": 2},
        }
    }
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
    with pytest.raises(mailer.NoMailerAvailable) as info:
        mailer.send("S", "body", "a@tests.local")
    assert isinstance(info.value.__cause__, OSError)


# --- the real settings module, fed by the real environment -------------------

PROBE = """
import django, json
django.setup()
from django.conf import settings
print("MAILERS_JSON=" + json.dumps({
    "mailers": settings.MAILERS,
    "force_tls12": settings.EMAIL_FORCE_TLS_1_2,
    "default_from": settings.DEFAULT_FROM_EMAIL,
}))
"""


def _settings_with_environment(extra: dict[str, str]) -> dict:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("EMAIL_")
        and key not in ("MAIL_DEBUG", "DEFAULT_FROM_EMAIL")
    }
    env.update(extra)
    env["DJANGO_SETTINGS_MODULE"] = "ciso_assistant.settings"
    # Django's deprecation warnings are (Pending)DeprecationWarning subclasses;
    # a configured instance must start without any of them.
    completed = subprocess.run(
        [
            sys.executable,
            "-W",
            "error::DeprecationWarning",
            "-W",
            "error::PendingDeprecationWarning",
            "-c",
            PROBE,
        ],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    line = next(
        line
        for line in completed.stdout.splitlines()
        if line.startswith("MAILERS_JSON=")
    )
    return json.loads(line.removeprefix("MAILERS_JSON="))


def test_settings_module_builds_mailers_from_environment():
    probe = _settings_with_environment(
        {**ENV, "EMAIL_FORCE_TLS_1_2": "true", "DEFAULT_FROM_EMAIL": "noreply@example"}
    )
    assert list(probe["mailers"]) == ["default", "rescue"]
    primary = probe["mailers"]["default"]
    assert primary["BACKEND"] == "core.email_backend.EmailBackend"
    assert primary["OPTIONS"]["host"] == "smtp.example"
    assert primary["OPTIONS"]["port"] == 587
    assert primary["OPTIONS"]["use_tls"] is True
    assert probe["mailers"]["rescue"]["OPTIONS"]["host"] == "smtp2.example"
    assert probe["force_tls12"] is True
    assert probe["default_from"] == "noreply@example"


def test_settings_module_with_nothing_configured_disables_mailing():
    probe = _settings_with_environment({})
    assert probe["mailers"] == {}


def test_settings_module_mail_debug_uses_console_and_default_sender():
    probe = _settings_with_environment({**ENV, "MAIL_DEBUG": "true"})
    assert probe["mailers"] == {
        "default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}
    }
    assert probe["default_from"] == "noreply@ciso.assistant"
