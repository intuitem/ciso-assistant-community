"""Build Django's ``MAILERS`` setting from the environment.

The environment variable names (``EMAIL_HOST``, ``EMAIL_HOST_RESCUE``, ...)
are the operator interface and never change. What they feed is Django's
``MAILERS`` dict, tried in declaration order by ``core.mailer``: the primary
SMTP server first, the rescue server second. The console backend replaces
both when ``MAIL_DEBUG`` is on.
"""

from collections.abc import Mapping

SMTP_BACKEND = "core.email_backend.EmailBackend"
CONSOLE_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Alias order is failover order.
ALIASES = ("default", "rescue")


def _flag(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "False").lower() in ("true", "1", "yes")


def smtp_mailer(env: Mapping[str, str], suffix: str = "") -> dict | None:
    """One SMTP mailer from ``EMAIL_*{suffix}`` variables, or None when the
    host is unset. Raises ValueError on contradictory TLS settings, as the
    settings module always did."""
    host = env.get(f"EMAIL_HOST{suffix}")
    if not host:
        return None
    use_tls = _flag(env, f"EMAIL_USE_TLS{suffix}")
    use_ssl = _flag(env, f"EMAIL_USE_SSL{suffix}")
    if use_tls and use_ssl:
        raise ValueError(
            f"EMAIL_USE_TLS{suffix} and EMAIL_USE_SSL{suffix} are mutually exclusive"
        )
    port = env.get(f"EMAIL_PORT{suffix}") or None
    if port is not None and port.isdigit():
        port = int(port)
    return {
        "BACKEND": SMTP_BACKEND,
        "OPTIONS": {
            "host": host,
            "port": port,
            "username": env.get(f"EMAIL_HOST_USER{suffix}") or None,
            "password": env.get(f"EMAIL_HOST_PASSWORD{suffix}") or None,
            "use_tls": use_tls,
            "use_ssl": use_ssl,
            "timeout": int(env.get("EMAIL_TIMEOUT", "5")),
        },
    }


def build_mailers(env: Mapping[str, str], *, mail_debug: bool = False) -> dict:
    """``MAILERS`` for the given environment. Empty when no server is
    configured: mailing is then off and ``core.mailer`` says so."""
    if mail_debug:
        return {"default": {"BACKEND": CONSOLE_BACKEND}}
    configured = [
        mailer
        for mailer in (smtp_mailer(env), smtp_mailer(env, "_RESCUE"))
        if mailer is not None
    ]
    return dict(zip(ALIASES, configured))


def describe(mailers: Mapping[str, dict]) -> list[str]:
    """Startup log lines: backend and options, password redacted."""
    lines = []
    for alias, mailer in mailers.items():
        options = {
            key: value
            for key, value in mailer.get("OPTIONS", {}).items()
            if key != "password"
        }
        lines.append(f"mailer {alias}: {mailer['BACKEND']} {options}")
    return lines
