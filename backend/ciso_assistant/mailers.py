"""Build Django's ``MAILERS`` setting from the environment.

The environment variable names (``EMAIL_HOST``, ``EMAIL_HOST_RESCUE``, ...)
are the operator interface and never change. What they feed is Django's
``MAILERS`` dict, tried in declaration order by ``core.mailer``: the primary
server first, the rescue server second. The console backend replaces both
when ``MAIL_DEBUG`` is on.

``EMAIL_TRANSPORT`` (and ``EMAIL_TRANSPORT_RESCUE``) selects how a mailer
sends: ``smtp`` with a password, the default, ``smtp-oauth2`` with a bearer
token obtained through one of the standard OAuth 2.0 grants, or ``graph``,
Microsoft Graph over HTTPS. There are no provider presets for SMTP: the
operator supplies host, token endpoint, grant and scope, and the
documentation gives the values for the common providers. Graph has one
provider by definition; its endpoints are Microsoft's.
"""

import re
from collections.abc import Mapping
from urllib.parse import urlsplit

SMTP_BACKEND = "core.email_backend.EmailBackend"
GRAPH_BACKEND = "core.graph_backend.EmailBackend"
CONSOLE_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Alias order is failover order.
ALIASES = ("default", "rescue")

TRANSPORTS = ("smtp", "smtp-oauth2", "graph")
GRANTS = ("client_credentials", "refresh_token", "jwt_bearer")

OAUTH2_SECRET_KEYS = ("client_secret", "refresh_token", "private_key")


def _flag(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "False").lower() in ("true", "1", "yes")


def oauth2_problems(config: dict) -> list[str]:
    """Every reason this OAuth configuration is unusable, as operator-facing
    messages. Empty when it is usable. Never raises, so callers that answer
    HTTP requests can report a problem without surfacing an exception."""
    grant = config.get("grant_type")
    if grant not in GRANTS:
        return [f"EMAIL_OAUTH2_GRANT_TYPE must be one of {', '.join(GRANTS)}"]
    problems = []
    token_url = config.get("token_url")
    if not token_url:
        problems.append("EMAIL_OAUTH2_TOKEN_URL is required")
    else:
        try:
            scheme = urlsplit(token_url).scheme
        except ValueError:
            scheme = None
        if scheme != "https":
            problems.append("EMAIL_OAUTH2_TOKEN_URL must use https")
    if not config.get("user"):
        problems.append("EMAIL_HOST_USER (the mailbox to send as) is required")
    required = {
        "client_credentials": ("client_id", "client_secret"),
        # RFC 6749 section 6: a public client refreshes without a secret.
        "refresh_token": ("client_id", "refresh_token"),
        "jwt_bearer": (),
    }[grant]
    missing = [name for name in required if not config.get(name)]
    if missing:
        names = ", ".join(f"EMAIL_OAUTH2_{name.upper()}" for name in missing)
        problems.append(f"{names} required for the {grant} grant")
    if grant == "jwt_bearer" and not (
        config.get("service_account_file")
        or (config.get("issuer") and config.get("private_key"))
    ):
        problems.append(
            "EMAIL_OAUTH2_SERVICE_ACCOUNT_FILE, or EMAIL_OAUTH2_ISSUER and "
            "EMAIL_OAUTH2_PRIVATE_KEY, required for the jwt_bearer grant"
        )
    return problems


def validate_oauth2(config: dict) -> None:
    """Fail loudly at startup on an unusable OAuth configuration."""
    problems = oauth2_problems(config)
    if problems:
        raise ValueError(problems[0])


def oauth2_config(env: Mapping[str, str], suffix: str, timeout: int) -> dict:
    """The ``oauth2`` option for an ``smtp-oauth2`` mailer, validated so a
    broken configuration stops startup instead of failing at send time.
    ``timeout`` bounds the token request like the SMTP connection."""

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
        "timeout": timeout,
    }
    try:
        validate_oauth2(config)
    except ValueError as error:
        raise ValueError(f"{error} (mailer{suffix or ' default'})") from error
    return config


# A tenant is a GUID or a verified domain name. Anything else cannot be part
# of the token URL.
_TENANT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")


def graph_problems(config: dict) -> list[str]:
    """Every reason this Graph configuration is unusable, as operator-facing
    messages. Empty when it is usable. Never raises."""
    problems = []
    tenant = config.get("tenant_id")
    if not tenant:
        problems.append("EMAIL_GRAPH_TENANT_ID is required")
    elif not _TENANT_ID.match(tenant):
        problems.append("EMAIL_GRAPH_TENANT_ID must be a tenant GUID or domain name")
    if not config.get("mailbox"):
        problems.append("EMAIL_HOST_USER (the mailbox to send as) is required")
    missing = [name for name in ("client_id", "client_secret") if not config.get(name)]
    if missing:
        names = ", ".join(f"EMAIL_OAUTH2_{name.upper()}" for name in missing)
        problems.append(f"{names} required for Microsoft Graph")
    return problems


def graph_entry(config: dict, timeout: int) -> dict:
    """The ``MAILERS`` entry for a validated Graph configuration."""
    from core.graph_backend import token_config

    return {
        "BACKEND": GRAPH_BACKEND,
        "OPTIONS": {
            "mailbox": config["mailbox"],
            "oauth2": token_config(
                tenant_id=config["tenant_id"],
                client_id=config["client_id"],
                client_secret=config["client_secret"],
                mailbox=config["mailbox"],
                timeout=timeout,
            ),
            "timeout": timeout,
        },
    }


def graph_mailer(env: Mapping[str, str], suffix: str = "") -> dict:
    """One Microsoft Graph mailer from the environment. The tenant, the
    client credentials and the mailbox are required; there is no host."""
    config = {
        "tenant_id": env.get(f"EMAIL_GRAPH_TENANT_ID{suffix}") or None,
        "client_id": env.get(f"EMAIL_OAUTH2_CLIENT_ID{suffix}") or None,
        "client_secret": env.get(f"EMAIL_OAUTH2_CLIENT_SECRET{suffix}") or None,
        "mailbox": env.get(f"EMAIL_HOST_USER{suffix}") or None,
    }
    problems = graph_problems(config)
    if problems:
        raise ValueError(f"{problems[0]} (mailer{suffix or ' default'})")
    return graph_entry(config, int(env.get("EMAIL_TIMEOUT", "15")))


def _transport(env: Mapping[str, str], suffix: str) -> str:
    transport = (env.get(f"EMAIL_TRANSPORT{suffix}") or "smtp").lower()
    if transport not in TRANSPORTS:
        raise ValueError(
            f"EMAIL_TRANSPORT{suffix} must be one of {', '.join(TRANSPORTS)}"
        )
    return transport


def env_mailer(env: Mapping[str, str], suffix: str = "") -> dict | None:
    """The mailer ``EMAIL_*{suffix}`` describes, whatever its transport, or
    None when nothing is configured."""
    if _transport(env, suffix) == "graph":
        return graph_mailer(env, suffix)
    return smtp_mailer(env, suffix)


def smtp_mailer(env: Mapping[str, str], suffix: str = "") -> dict | None:
    """One SMTP mailer from ``EMAIL_*{suffix}`` variables, or None when
    nothing is configured. Raises ValueError on contradictory TLS settings, as
    the settings module always did, on a non-numeric port, and on an unusable
    OAuth configuration. An unset port is 465 with SSL and 25 otherwise,
    STARTTLS included, as before ``MAILERS``."""
    transport = _transport(env, suffix)
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
    if transport == "smtp-oauth2" and not (use_tls or use_ssl):
        raise ValueError(
            f"EMAIL_TRANSPORT{suffix}=smtp-oauth2 requires EMAIL_USE_TLS{suffix} or "
            f"EMAIL_USE_SSL{suffix}: the bearer token must not be sent in clear"
        )
    port = env.get(f"EMAIL_PORT{suffix}") or None
    if port is not None:
        if not port.isdigit():
            raise ValueError(f"EMAIL_PORT{suffix} must be a number, got {port!r}")
        port = int(port)
    elif not use_ssl:
        # Before MAILERS an unset port reached smtplib as 0, which is 25 even
        # with STARTTLS. Django's mailers would pick 587; keep 25 so existing
        # deployments connect where they always did.
        port = 25

    options = {
        "host": host,
        "port": port,
        "username": env.get(f"EMAIL_HOST_USER{suffix}") or None,
        "password": env.get(f"EMAIL_HOST_PASSWORD{suffix}") or None,
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "timeout": int(env.get("EMAIL_TIMEOUT", "5")),
    }
    # Client certificate for relays that require one; the TLS 1.2 pin in
    # core.email_backend applies on top of it.
    for option in ("ssl_certfile", "ssl_keyfile"):
        value = env.get(f"EMAIL_{option.upper()}{suffix}")
        if value:
            options[option] = value
    if transport == "smtp-oauth2":
        options["password"] = None
        options["oauth2"] = oauth2_config(env, suffix, options["timeout"])
    return {"BACKEND": SMTP_BACKEND, "OPTIONS": options}


def build_mailers(env: Mapping[str, str], *, mail_debug: bool = False) -> dict:
    """``MAILERS`` for the given environment. Empty when no server is
    configured: mailing is then off and ``core.mailer`` says so."""
    if mail_debug:
        return {"default": {"BACKEND": CONSOLE_BACKEND}}
    configured = [
        mailer
        for mailer in (env_mailer(env), env_mailer(env, "_RESCUE"))
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
