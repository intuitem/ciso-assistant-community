"""OAuth 2.0 access tokens for SMTP authentication (SASL XOAUTH2).

The SMTP side of XOAUTH2 is one mechanism whoever issued the token. The token
side is one of three standard grants:

- ``client_credentials`` (RFC 6749): client id and secret. Microsoft 365.
- ``jwt_bearer`` (RFC 7523): a JWT signed with a private key, naming the user
  to act as. Google Workspace service accounts with domain-wide delegation.
- ``refresh_token`` (RFC 6749): a long-lived refresh token obtained once by a
  person. Providers that offer no machine flow.

Tokens are cached per configuration until shortly before they expire. The
token endpoint is an operator-supplied URL at the same trust level as
``EMAIL_HOST``, so it may point at a private identity provider; it must use
HTTPS because the response carries a bearer secret.
"""

import json
import threading
import time
import httpx
import jwt
import structlog

from ciso_assistant.mailers import GRANTS  # noqa: F401  (re-exported for callers)

logger = structlog.get_logger(__name__)

JWT_BEARER_GRANT = "urn:ietf:params:oauth:grant-type:jwt-bearer"
EXPIRY_MARGIN_SECONDS = 60
ASSERTION_LIFETIME_SECONDS = 3600
DEFAULT_TIMEOUT_SECONDS = 15

# Tests swap in httpx.MockTransport; None means the default transport.
TRANSPORT = None

_cache: dict[tuple, tuple[str, float]] = {}
_lock = threading.Lock()


class TokenError(Exception):
    """The token endpoint could not be reached or refused to issue a token."""


def xoauth2_string(user: str, token: str) -> str:
    """The SASL XOAUTH2 initial response, before base64 (smtplib encodes)."""
    return f"user={user}\x01auth=Bearer {token}\x01\x01"


def _cache_key(config: dict) -> tuple:
    return (
        config["token_url"],
        config.get("client_id"),
        config.get("issuer") or config.get("service_account_file"),
        config.get("user"),
        config.get("scope"),
    )


def get_token(config: dict, *, force_refresh: bool = False) -> str:
    """A valid access token for ``config``, from the cache when possible."""
    key = _cache_key(config)
    now = time.monotonic()
    if not force_refresh:
        with _lock:
            cached = _cache.get(key)
        if cached is not None and cached[1] > now:
            return cached[0]
    token, expires_in = fetch_token(config)
    with _lock:
        _cache[key] = (token, now + max(expires_in - EXPIRY_MARGIN_SECONDS, 0))
    return token


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def fetch_token(config: dict) -> tuple[str, int]:
    """Ask the token endpoint for a token. Returns it with its lifetime."""
    token_url = config["token_url"]
    payload = _grant_payload(config)
    timeout = config.get("timeout") or DEFAULT_TIMEOUT_SECONDS
    try:
        with httpx.Client(timeout=timeout, transport=TRANSPORT) as client:
            response = client.post(token_url, data=payload)
    except httpx.HTTPError as error:
        raise TokenError(f"token endpoint unreachable: {error}") from error
    if response.status_code != 200:
        raise TokenError(
            f"token endpoint answered {response.status_code}: {_error_text(response)}"
        )
    try:
        body = response.json()
    except ValueError as error:
        raise TokenError("token endpoint returned a non-JSON body") from error
    token = body.get("access_token")
    if not token:
        raise TokenError("token endpoint returned no access_token")
    try:
        expires_in = int(body.get("expires_in", ASSERTION_LIFETIME_SECONDS))
    except (TypeError, ValueError):
        expires_in = ASSERTION_LIFETIME_SECONDS
    logger.info(
        "oauth2 token obtained",
        token_url=token_url,
        grant=config["grant_type"],
        expires_in=expires_in,
    )
    return token, expires_in


def _error_text(response: httpx.Response) -> str:
    # OAuth error bodies are JSON with "error" and "error_description"; never
    # echo an arbitrary body into logs or exceptions.
    try:
        body = response.json()
    except ValueError:
        return "no OAuth error body"
    if not isinstance(body, dict):
        return "no OAuth error body"
    error = body.get("error", "")
    description = body.get("error_description", "")
    return f"{error} {description}".strip() or "no OAuth error body"


def _grant_payload(config: dict) -> dict:
    grant = config["grant_type"]
    if grant == "client_credentials":
        payload = {
            "grant_type": grant,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
        }
        if config.get("scope"):
            payload["scope"] = config["scope"]
        return payload
    if grant == "refresh_token":
        return {
            "grant_type": grant,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "refresh_token": config["refresh_token"],
        }
    return {"grant_type": JWT_BEARER_GRANT, "assertion": _signed_assertion(config)}


def _signed_assertion(config: dict) -> str:
    issuer, private_key = _signing_identity(config)
    now = int(time.time())
    claims = {
        "iss": issuer,
        "sub": config["user"],
        "aud": config.get("audience") or config["token_url"],
        "iat": now,
        "exp": now + ASSERTION_LIFETIME_SECONDS,
    }
    if config.get("scope"):
        claims["scope"] = config["scope"]
    return jwt.encode(claims, private_key, algorithm="RS256")


def _signing_identity(config: dict) -> tuple[str, str]:
    path = config.get("service_account_file")
    if path:
        try:
            with open(path, encoding="utf-8") as handle:
                account = json.load(handle)
            return account["client_email"], account["private_key"]
        except (OSError, ValueError, KeyError) as error:
            raise TokenError(
                f"cannot read service account file {path!r}: {error}"
            ) from error
    return config["issuer"], config["private_key"]
