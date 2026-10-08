"""The SMTP email backend behind every SMTP mailer.

Two things on top of Django's backend:

- ``EMAIL_FORCE_TLS_1_2``. Django 6 removed the ``ssl_context`` kwarg and
  turned it into a ``cached_property`` built from the ``ssl_certfile`` /
  ``ssl_keyfile`` options, so the TLS 1.2 pin has to be applied here.
- OAuth 2.0 over SMTP (SASL XOAUTH2). When the mailer carries an ``oauth2``
  option, the connection authenticates with a bearer token obtained by
  ``core.mail_oauth2`` instead of a password. The username stays the mailbox
  to send as.
"""

import smtplib
import ssl

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend
from django.utils.functional import cached_property

from core import mail_oauth2


def pin_tls12(context: ssl.SSLContext) -> ssl.SSLContext:
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers("ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256")
    return context


class EmailBackend(SMTPEmailBackend):
    def __init__(self, *args, oauth2=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.oauth2 = oauth2
        if oauth2:
            # No password: the parent's open() then skips password login and
            # we authenticate with the token ourselves.
            self.password = None

    @cached_property
    def ssl_context(self):
        # Pin Django's own context in place so a client certificate passed in
        # OPTIONS keeps applying alongside the TLS 1.2 restriction.
        context = super().ssl_context
        if getattr(settings, "EMAIL_FORCE_TLS_1_2", False):
            pin_tls12(context)
        return context

    def open(self):
        opened = super().open()
        if opened and self.oauth2:
            try:
                self._authenticate_oauth2()
            except Exception:
                # A failed authentication is an unreachable mailer: release
                # the socket and let core.mailer fail over.
                self._drop_connection()
                raise
        return opened

    def _authenticate_oauth2(self):
        connection = self.connection
        connection.ehlo_or_helo_if_needed()
        token = mail_oauth2.get_token(self.oauth2)
        try:
            _auth_xoauth2(connection, self.username, token)
        except smtplib.SMTPAuthenticationError:
            # The cached token may have been revoked or expired early; one
            # retry with a freshly issued token, then give up.
            token = mail_oauth2.get_token(self.oauth2, force_refresh=True)
            _auth_xoauth2(connection, self.username, token)

    def _drop_connection(self):
        connection, self.connection = self.connection, None
        if connection is None:
            return
        try:
            connection.close()
        except Exception:
            pass


def _auth_xoauth2(connection: smtplib.SMTP, user: str, token: str) -> None:
    initial = mail_oauth2.xoauth2_string(user, token)

    def authobject(challenge=None):
        # On failure the server sends a challenge carrying its error; the
        # client answers with an empty line to receive the final 535.
        return initial if challenge is None else ""

    connection.auth("XOAUTH2", authobject)
