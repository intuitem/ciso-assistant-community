"""Build Django's ``MAILERS`` setting from the environment.

The environment variable names (``EMAIL_HOST``, ``EMAIL_HOST_RESCUE``, ...)
are the operator interface and never change. What they feed is Django's
``MAILERS`` dict, tried in declaration order by ``core.mailer``: the primary
server first, the rescue server second. The console backend replaces both
when ``MAIL_DEBUG`` is on.

``EMAIL_TRANSPORT`` (and ``EMAIL_TRANSPORT_RESCUE``) selects how a mailer
authenticates: ``smtp`` with a password, the default, or ``smtp-oauth2`` with
a bearer token obtained through one of the standard OAuth 2.0 grants. There
are no provider presets: the operator supplies host, token endpoint, grant
and scope, and the documentation gives the values for the common providers.
"""

from collections.abc import Mapping
from urllib.parse import urlsplit

SMTP_BACKEND = "core.email_backend.EmailBackend"
CONSOLE_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Alias order is failover order.
ALIASES = ("default", "rescue")

TRANSPORTS = ("smtp", "smtp-oauth2")
GRANTS = ("client_credentials", "refresh_token", "jwt_bearer")

OAUTH2_SECRET_KEYS = ("client_secret", "refresh_token", "private_key")


def _flag(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "False").lower() in ("true", "1", "yes")


def validate_oauth2(config: dict) -> None:
    """Fail loudly at startup on an unusable OAuth configuration."""
    grant = config.get("grant_type")
    if grant not in GRANTS:
        raise ValueError(f"EMAIL_OAUTH2_GRANT_TYPE must be one of {', '.join(GRANTS)}")
    token_url = config.get("token_url")
    if not token_url:
        raise ValueError("EMAIL_OAUTH2_TOKEN_URL is required")
    if urlsplit(token_url).scheme != "https":
        raise ValueError("EMAIL_OAUTH2_TOKEN_URL must use https")
    if not config.get("user"):
        raise ValueError("EMAIL_HOST_USER (the mailbox to send as) is required")
    required = {
        "client_credentials": ("client_id", "client_secret"),
        "refresh_token": ("client_id", "client_secret", "refresh_token"),
        "jwt_bearer": (),
    }[grant]
    missing = [name for name in required if not config.get(name)]
    if missing:
        names = ", ".join(f"EMAIL_OAUTH2_{name.upper()}" for name in missing)
        raise ValueError(f"{names} required for the {grant} grant")
    if grant == "jwt_bearer" and not (
        config.get("service_account_file")
        or (config.get("issuer") and config.get("private_key"))
    ):
        raise ValueError(
            "EMAIL_OAUTH2_SERVICE_ACCOUNT_FILE, or EMAIL_OAUTH2_ISSUER and "
            "EMAIL_OAUTH2_PRIVATE_KEY, required for the jwt_bearer grant"
        )


def oauth2_config(env: Mapping[str, str], suffix: str) -> dict:
    """The ``oauth2`` option for an ``smtp-oauth2`` mailer, validated so a
    broken configuration stops startup instead of failing at send time."""

    def var(name: str) -> str | None:
        return env.get(f"EMAIL_OAUTH2_{name}{suffix}") or None

    config = {
        "user": env.get(f"EMAIL_HOST_USER{suffix}") or None,
        "grant_type": var("GRANT_TYPE"),
        "token_url": var("TOKEN_URL"),
        "scope": var("SCOPE"),
        "client_id": var("CLIENT_ID"),
        "client_secret": var("CLIENT_SECRET"),
        "refresh_token": var("REFRESH_TOKEN"),
        "service_account_file": var("SERVICE_ACCOUNT_FILE"),
        "issuer": var("ISSUER"),
        "private_key": var("PRIVATE_KEY"),
        "audience": var("AUDIENCE"),
    }
    try:
        validate_oauth2(config)
    except ValueError as error:
        raise ValueError(f"{error} (mailer{suffix or ' default'})") from error
    return config


def smtp_mailer(env: Mapping[str, str], suffix: str = "") -> dict | None:
    """One SMTP mailer from ``EMAIL_*{suffix}`` variables, or None when
    nothing is configured. Raises ValueError on contradictory TLS settings, as
    the settings module always did, on a non-numeric port, and on an unusable
    OAuth configuration. An unset port is left to the backend: 465 with SSL,
    587 with STARTTLS, 25 otherwise."""
    transport = (env.get(f"EMAIL_TRANSPORT{suffix}") or "smtp").lower()
    if transport not in TRANSPORTS:
        raise ValueError(
            f"EMAIL_TRANSPORT{suffix} must be one of {', '.join(TRANSPORTS)}"
        )
    host = env.get(f"EMAIL_HOST{suffix}")
    if not host:
        if transport == "smtp-oauth2":
            raise ValueError(
                f"EMAIL_HOST{suffix} is required with EMAIL_TRANSPORT{suffix}=smtp-oauth2"
            )
        return None

    use_tls = _flag(env, f"EMAIL_USE_TLS{suffix}")
    use_ssl = _flag(env, f"EMAIL_USE_SSL{suffix}")
    if use_tls and use_ssl:
        raise ValueError(
            f"EMAIL_USE_TLS{suffix} and EMAIL_USE_SSL{suffix} are mutually exclusive"
        )
    port = env.get(f"EMAIL_PORT{suffix}") or None
    if port is not None:
        if not port.isdigit():
            raise ValueError(f"EMAIL_PORT{suffix} must be a number, got {port!r}")
        port = int(port)

    options = {
        "host": host,
        "port": port,
        "username": env.get(f"EMAIL_HOST_USER{suffix}") or None,
        "password": env.get(f"EMAIL_HOST_PASSWORD{suffix}") or None,
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "timeout": int(env.get("EMAIL_TIMEOUT", "5")),
    }
    if transport == "smtp-oauth2":
        options["password"] = None
        options["oauth2"] = oauth2_config(env, suffix)
    return {"BACKEND": SMTP_BACKEND, "OPTIONS": options}


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
    """Startup log lines: backend and options, every secret redacted."""
    lines = []
    for alias, mailer in mailers.items():
        options = {
            key: value
            for key, value in mailer.get("OPTIONS", {}).items()
            if key != "password"
        }
        if "oauth2" in options:
            options["oauth2"] = {
                key: ("***" if key in OAUTH2_SECRET_KEYS and value else value)
                for key, value in options["oauth2"].items()
            }
        lines.append(f"mailer {alias}: {mailer['BACKEND']} {options}")
    return lines
