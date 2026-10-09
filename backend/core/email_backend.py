"""The SMTP email backend behind every SMTP mailer.

Two things on top of Django's backend:

- The TLS context. Django 6 removed the ``ssl_context`` kwarg and builds the
  context itself; with a client certificate it builds a bare one that trusts
  no CA, so no server certificate verifies. We build it from the default
  context instead, add the client certificate, and apply
  ``EMAIL_FORCE_TLS_1_2``.
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
        # Not super().ssl_context: with a client certificate Django returns
        # SSLContext(PROTOCOL_TLS_CLIENT) without the system trust store.
        context = ssl.create_default_context()
        if self.ssl_certfile or self.ssl_keyfile:
            context.load_cert_chain(self.ssl_certfile, self.ssl_keyfile)
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
        try:
            self._authenticate_with(mail_oauth2.get_token(self.oauth2))
            return
        except smtplib.SMTPAuthenticationError:
            # The cached token may have been revoked or expired early. The
            # session is still usable for a second attempt.
            pass
        except smtplib.SMTPServerDisconnected:
            # Servers commonly delay the answer to a failed login, and the
            # delay can outlast the timeout. The session is gone: start a new
            # one for the retry.
            self._drop_connection()
            super().open()
        # One retry with a freshly issued token, then give up.
        self._authenticate_with(mail_oauth2.get_token(self.oauth2, force_refresh=True))

    def _authenticate_with(self, token: str):
        try:
            self.connection.ehlo_or_helo_if_needed()
            _auth_xoauth2(self.connection, self.username, token)
        except Exception:
            # A token that did not get us in is never offered again, whatever
            # the failure: otherwise it would be reused until it expires.
            mail_oauth2.discard(self.oauth2, token)
            raise

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
