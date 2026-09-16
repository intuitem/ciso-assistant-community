"""SMTP email backend honouring the EMAIL_FORCE_TLS_1_2 setting.

Django 6 removed the ``ssl_context`` kwarg from the SMTP backend and turned it
into a ``cached_property`` built from ``EMAIL_SSL_CERTFILE`` /
``EMAIL_SSL_KEYFILE``. Passing ``ssl_context=`` to ``get_connection()`` is now
silently dropped, so the TLS 1.2 pin has to be applied by the backend itself.
"""

import ssl

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend
from django.utils.functional import cached_property


def build_tls12_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers("ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256")
    return context


class EmailBackend(SMTPEmailBackend):
    @cached_property
    def ssl_context(self):
        if getattr(settings, "EMAIL_FORCE_TLS_1_2", False):
            return build_tls12_context()
        return super().ssl_context
