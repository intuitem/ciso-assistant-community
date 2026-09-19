"""Regression tests for the EMAIL_FORCE_TLS_1_2 SMTP backend.

Django 6 dropped the ``ssl_context`` kwarg on the SMTP backend, which turned
the setting into a silent no-op. The pin now lives in ``core.email_backend``.
"""

import ssl
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils.module_loading import import_string

from ciso_assistant import settings as project_settings
from core.email_backend import EmailBackend


@override_settings(EMAIL_FORCE_TLS_1_2=True)
def test_ssl_context_is_pinned_to_tls12_when_flag_on():
    context = EmailBackend().ssl_context
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert context.maximum_version == ssl.TLSVersion.TLSv1_2
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


@override_settings(EMAIL_FORCE_TLS_1_2=True)
def test_tls12_pin_keeps_client_certificate():
    with patch.object(ssl.SSLContext, "load_cert_chain") as load_cert_chain:
        context = EmailBackend(
            ssl_certfile="/etc/ssl/client.pem", ssl_keyfile="/etc/ssl/client.key"
        ).ssl_context
    load_cert_chain.assert_called_once_with(
        "/etc/ssl/client.pem", "/etc/ssl/client.key"
    )
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert context.maximum_version == ssl.TLSVersion.TLSv1_2


@override_settings(EMAIL_FORCE_TLS_1_2=False)
def test_ssl_context_is_default_when_flag_off():
    context = EmailBackend().ssl_context
    default = ssl.create_default_context()
    assert isinstance(context, ssl.SSLContext)
    assert context.minimum_version == default.minimum_version
    assert context.maximum_version == default.maximum_version
    assert context.maximum_version == ssl.TLSVersion.MAXIMUM_SUPPORTED
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.skipif(
    project_settings.MAIL_DEBUG, reason="MAIL_DEBUG swaps in the console backend"
)
def test_project_email_backend_is_wired():
    # pytest-django forces locmem on django.conf.settings, so read the module.
    assert import_string(project_settings.EMAIL_BACKEND) is EmailBackend
