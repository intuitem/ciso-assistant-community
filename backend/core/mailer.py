"""Outgoing mail service.

Every message the application sends goes through here. The mailers come from
the custom configuration an administrator stored in the app when
``ENABLE_CUSTOM_MAILER`` is set and that configuration is active, otherwise
from ``settings.MAILERS`` (built from the environment in
``ciso_assistant.mailers``). They are tried in order. Failover happens only
when a mailer cannot be opened; once a message has been handed to a
connection, any failure is final and propagates, so a message is never sent
twice.

Every attempt updates the mailer's delivery health row, best effort: health is
observability and must never break a send.

The service is synchronous and raises on failure. Callers that must not block
wrap it in a Huey task that reports the outcome (see the workflow ``send_email``
action). Nothing here swallows errors.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field

import structlog
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from django.utils.module_loading import import_string

logger = structlog.get_logger(__name__)

DEFAULT_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
SOURCE_ENVIRONMENT = "environment"
SOURCE_CUSTOM = "custom"


class NoMailerAvailable(Exception):
    """No mailer is configured, or none accepted a connection."""


@dataclass(frozen=True)
class MailerSpec:
    """One mailer to try: a backend class and its constructor options."""

    alias: str
    backend: str
    options: dict
    source: str = SOURCE_ENVIRONMENT

    def build(self):
        return import_string(self.backend)(alias=self.alias, **self.options)


def environment_mailers() -> list[MailerSpec]:
    return [
        MailerSpec(
            alias,
            entry.get("BACKEND", DEFAULT_BACKEND),
            dict(entry.get("OPTIONS", {})),
            SOURCE_ENVIRONMENT,
        )
        for alias, entry in (getattr(settings, "MAILERS", None) or {}).items()
    ]


def custom_configuration():
    """The stored configuration when the switch is on and it is active with
    at least one mailer, else None. Never touches the database otherwise."""
    if not getattr(settings, "ENABLE_CUSTOM_MAILER", False):
        return None
    from global_settings.models import MailerConfiguration

    configuration = (
        MailerConfiguration.objects.filter(is_active=True)
        .order_by("created_at")
        .first()
    )
    if configuration is None or not configuration.mailers.exists():
        return None
    return configuration


def custom_mailers(configuration) -> list[MailerSpec]:
    specs = []
    for row in configuration.mailers.all():
        try:
            entry = row.mailer_entry()
        except ValueError as error:
            logger.error(
                "stored mailer is unusable, skipped", mailer=row.alias, error=str(error)
            )
            continue
        specs.append(
            MailerSpec(row.alias, entry["BACKEND"], entry["OPTIONS"], SOURCE_CUSTOM)
        )
    return specs


def active_mailers() -> list[MailerSpec]:
    configuration = custom_configuration()
    if configuration is not None:
        return custom_mailers(configuration)
    return environment_mailers()


def sender_address() -> str | None:
    configuration = custom_configuration()
    if configuration is not None and configuration.from_email:
        return configuration.from_email
    return getattr(settings, "DEFAULT_FROM_EMAIL", None) or None


def mailer_aliases() -> list[str]:
    return [spec.alias for spec in active_mailers()]


def missing_configuration() -> list[str]:
    """Operator-facing names of what is missing before mail can be sent.
    Empty when mailing is enabled."""
    missing = []
    if not active_mailers():
        missing.append("EMAIL_HOST")
    if not sender_address():
        missing.append("DEFAULT_FROM_EMAIL")
    return missing


def mailing_enabled() -> bool:
    """True when at least one mailer and a sender address are configured."""
    return not missing_configuration()


@contextmanager
def open_connection(
    attempts: list | None = None,
    mailers: list[MailerSpec] | None = None,
    record_health: bool = True,
):
    """Yield the first mailer that accepts a connection, closed on exit.

    ``attempts``, when given, collects ``(alias, error)`` for every mailer
    that could not be opened, so a caller can report the failover path.
    ``mailers`` overrides the active list, for testing a configuration before
    it is saved and for notifying through the mailers a change replaced.
    ``record_health`` is off for such draft attempts, so a test of unsaved
    values never rewrites the health of the mailer that is actually in use.

    This is the only place failover happens. An exception raised by the
    caller while the connection is open propagates unchanged: the next
    mailer is not tried, because the server may already have the message.
    """
    specs = active_mailers() if mailers is None else list(mailers)
    if not specs:
        raise NoMailerAvailable("no mailer configured (set EMAIL_HOST)")
    last_error = None
    skipped = 0
    for spec in specs:
        backend = spec.build()
        try:
            backend.open()
        except Exception as error:
            logger.error(
                "mailer unreachable, trying the next one",
                mailer=spec.alias,
                backend=type(backend).__name__,
                error=str(error),
            )
            if attempts is not None:
                attempts.append((spec.alias, str(error)))
            if record_health:
                _record_health(
                    spec, "unreachable", error=str(error), via_failover=skipped > 0
                )
            skipped += 1
            last_error = error
            # A failed login or STARTTLS leaves the socket half open on the
            # backend; release it before moving on.
            _close(backend, spec.alias)
            continue
        try:
            yield backend
        except Exception as error:
            if record_health:
                _record_health(
                    spec, "failed", error=str(error), via_failover=skipped > 0
                )
            raise
        else:
            if record_health:
                _record_health(spec, "ok", via_failover=skipped > 0)
        finally:
            _close(backend, spec.alias)
        return
    raise NoMailerAvailable(
        f"no mailer reachable, tried {', '.join(spec.alias for spec in specs)}"
    ) from last_error


def _close(backend, alias: str) -> None:
    """Closing is cleanup: a failed QUIT must not turn a message the server
    already accepted into a reported failure, nor mask the caller's error."""
    try:
        backend.close()
    except Exception as error:
        logger.warning(
            "mailer connection did not close cleanly", mailer=alias, error=str(error)
        )


def _record_health(
    spec: MailerSpec, outcome: str, *, error: str = "", via_failover: bool
) -> None:
    """Update the mailer's health row. Best effort: a failure here is logged
    and never surfaces to the send."""
    try:
        from global_settings.models import MailerHealth

        now = timezone.now()
        defaults = {
            "source": spec.source,
            "last_attempt_at": now,
            "last_outcome": outcome,
            "last_error": error[:2000],
            "via_failover": via_failover,
        }
        if outcome == "ok":
            defaults["last_success_at"] = now
        MailerHealth.objects.update_or_create(alias=spec.alias, defaults=defaults)
    except Exception as health_error:
        logger.warning(
            "mailer health not recorded", mailer=spec.alias, error=str(health_error)
        )


def send(
    subject: str,
    body: str,
    recipient: str | list[str],
    *,
    html_body: str | None = None,
    from_email: str | None = None,
    connection=None,
    mailers: list[MailerSpec] | None = None,
) -> None:
    """Send one message. Pass ``connection`` (from ``open_connection``) to
    batch several sends on one session; the caller owns its lifecycle.

    Raises whatever the backend raises, and RuntimeError when the backend
    reports the message unsent without raising."""
    message = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email or sender_address(),
        to=[recipient] if isinstance(recipient, str) else list(recipient),
    )
    if html_body:
        message.content_subtype = "html"
        message.body = html_body
    if connection is not None:
        sent = connection.send_messages([message])
    else:
        with open_connection(mailers=mailers) as backend:
            sent = backend.send_messages([message])
    # Backends can report 0 sent without raising (filtered recipients, dummy
    # backends); that is a delivery failure, not a success.
    if sent != 1:
        raise RuntimeError(f"email backend reported {sent} of 1 messages sent")


@dataclass
class TestSendResult:
    """Outcome of a test send, for the management command and the UI."""

    ok: bool
    recipient: str
    mailer: str | None = None
    backend: str | None = None
    error: str | None = None
    skipped: list[tuple[str, str]] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.ok:
            return f"test email sent to {self.recipient} through mailer {self.mailer}"
        return f"test email to {self.recipient} failed: {self.error}"


def send_test(
    recipient: str,
    *,
    mailers: list[MailerSpec] | None = None,
    from_email: str | None = None,
    record_health: bool | None = None,
) -> TestSendResult:
    """Send a test message and report what happened instead of raising.

    The service's other entry points raise; this one is for a person who is
    checking the configuration and wants the answer, including which mailer
    delivered and which ones were skipped on the way. ``mailers`` and
    ``from_email`` test a configuration that is not saved yet; such draft
    tests do not touch delivery health unless ``record_health`` says so."""
    if mailers is None:
        missing = missing_configuration()
        if missing:
            return TestSendResult(
                ok=False,
                recipient=recipient,
                error=f"mail is not configured (missing {', '.join(missing)})",
            )
    sender = from_email or sender_address()
    if not sender:
        return TestSendResult(
            ok=False, recipient=recipient, error="no sender address configured"
        )
    skipped: list[tuple[str, str]] = []
    now = timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z")
    try:
        if record_health is None:
            record_health = mailers is None
        with open_connection(
            attempts=skipped, mailers=mailers, record_health=record_health
        ) as backend:
            alias = getattr(backend, "alias", None)
            backend_name = type(backend).__name__
            send(
                "CISO Assistant test email",
                f"This is a test email from CISO Assistant ({settings.CISO_ASSISTANT_URL}).\n"
                f"Sent on {now} through mailer '{alias}' ({backend_name}).\n"
                "If you received it, outgoing mail is configured correctly.",
                recipient,
                from_email=sender,
                connection=backend,
            )
    except Exception as error:
        return TestSendResult(
            ok=False, recipient=recipient, error=str(error), skipped=skipped
        )
    return TestSendResult(
        ok=True,
        recipient=recipient,
        mailer=alias,
        backend=backend_name,
        skipped=skipped,
    )
