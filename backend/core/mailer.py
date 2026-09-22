"""Outgoing mail service.

Every message the application sends goes through here. The mailers come from
``settings.MAILERS`` (built from the environment in ``ciso_assistant.mailers``)
and are tried in declaration order. Failover happens only when a mailer cannot
be opened; once a message has been handed to a connection, any failure is
final and propagates, so a message is never sent twice.

The service is synchronous and raises on failure. Callers that must not block
wrap it in a Huey task that reports the outcome (see the workflow ``send_email``
action). Nothing here swallows errors.
"""

from contextlib import contextmanager

import structlog
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils.module_loading import import_string

logger = structlog.get_logger(__name__)

DEFAULT_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


class NoMailerAvailable(Exception):
    """No mailer is configured, or none accepted a connection."""


def mailer_aliases() -> list[str]:
    return list(getattr(settings, "MAILERS", None) or {})


def missing_configuration() -> list[str]:
    """Operator-facing names of what is missing before mail can be sent.
    Empty when mailing is enabled."""
    missing = []
    if not mailer_aliases():
        missing.append("EMAIL_HOST")
    if not getattr(settings, "DEFAULT_FROM_EMAIL", None):
        missing.append("DEFAULT_FROM_EMAIL")
    return missing


def mailing_enabled() -> bool:
    """True when at least one mailer and a sender address are configured."""
    return not missing_configuration()


def _build(alias: str):
    config = settings.MAILERS[alias]
    backend_class = import_string(config.get("BACKEND", DEFAULT_BACKEND))
    return backend_class(alias=alias, **config.get("OPTIONS", {}))


@contextmanager
def open_connection():
    """Yield the first mailer that accepts a connection, closed on exit.

    This is the only place failover happens. An exception raised by the
    caller while the connection is open propagates unchanged: the next
    mailer is not tried, because the server may already have the message.
    """
    aliases = mailer_aliases()
    if not aliases:
        raise NoMailerAvailable("no mailer configured (set EMAIL_HOST)")
    last_error = None
    for alias in aliases:
        backend = _build(alias)
        try:
            backend.open()
        except Exception as error:
            logger.error(
                "mailer unreachable, trying the next one",
                mailer=alias,
                backend=type(backend).__name__,
                error=str(error),
            )
            last_error = error
            continue
        try:
            yield backend
        finally:
            backend.close()
        return
    raise NoMailerAvailable(
        f"no mailer reachable, tried {', '.join(aliases)}"
    ) from last_error


def send(
    subject: str,
    body: str,
    recipient: str | list[str],
    *,
    html_body: str | None = None,
    from_email: str | None = None,
    connection=None,
) -> None:
    """Send one message. Pass ``connection`` (from ``open_connection``) to
    batch several sends on one session; the caller owns its lifecycle.

    Raises whatever the backend raises, and RuntimeError when the backend
    reports the message unsent without raising."""
    message = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=[recipient] if isinstance(recipient, str) else list(recipient),
    )
    if html_body:
        message.content_subtype = "html"
        message.body = html_body
    if connection is not None:
        sent = connection.send_messages([message])
    else:
        with open_connection() as backend:
            sent = backend.send_messages([message])
    # Backends can report 0 sent without raising (filtered recipients, dummy
    # backends); that is a delivery failure, not a success.
    if sent != 1:
        raise RuntimeError(f"email backend reported {sent} of 1 messages sent")
