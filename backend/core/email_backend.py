"""SMTP email backend honouring the EMAIL_FORCE_TLS_1_2 setting.

Django 6 removed the ``ssl_context`` kwarg from the SMTP backend and turned it
into a ``cached_property`` built from the ``ssl_certfile`` / ``ssl_keyfile``
options, so the TLS 1.2 pin has to be applied by the backend itself.
"""

import ssl

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend
from django.utils.functional import cached_property


def pin_tls12(context: ssl.SSLContext) -> ssl.SSLContext:
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers("ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256")
    return context


class EmailBackend(SMTPEmailBackend):
    @cached_property
    def ssl_context(self):
        # Pin Django's own context in place so a client certificate passed in
        # OPTIONS keeps applying alongside the TLS 1.2 restriction.
        context = super().ssl_context
        if getattr(settings, "EMAIL_FORCE_TLS_1_2", False):
            pin_tls12(context)
        return context
