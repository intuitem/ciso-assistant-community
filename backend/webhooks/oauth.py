"""OAuth 2.0 client-credentials tokens for HTTP audit sinks.

Tokens are cached per process — Huey workers each hold their own — so a sink
fetches roughly one token per worker per token lifetime.
"""

import threading
import time

import requests
import structlog

from core.net_safety import assert_public_url_unless_dev

logger = structlog.get_logger(__name__)

# Renew early so a token can't expire in flight.
_EXPIRY_SKEW = 60
_DEFAULT_TTL = 3600

_cache: dict[tuple, tuple[str, float]] = {}
_lock = threading.Lock()


class OAuthError(Exception):
    """Token acquisition failed."""


def _key(endpoint) -> tuple:
    # Keyed on the credentials themselves so an edited sink can't be served a
    # token minted from the previous ones.
    cfg = endpoint.oauth_config or {}
    return (
        str(endpoint.id),
        cfg.get("token_url"),
        cfg.get("client_id"),
        cfg.get("scope"),
    )


def _fetch(cfg: dict) -> tuple[str, float]:
    token_url = cfg.get("token_url")
    if not token_url or not cfg.get("client_id"):
        raise OAuthError("oauth_config is missing token_url or client_id")

    # Same SSRF surface as the sink URL, and credentials must never travel over
    # plaintext HTTP, so this stays HTTPS-only.
    assert_public_url_unless_dev(token_url, allowed_schemes=("https",))

    data = {
        "grant_type": "client_credentials",
        "client_id": cfg["client_id"],
        "client_secret": cfg.get("client_secret", ""),
    }
    if cfg.get("scope"):
        data["scope"] = cfg["scope"]
    data.update(cfg.get("extra_params") or {})

    response = requests.post(token_url, data=data, timeout=15, allow_redirects=False)
    if response.status_code != 200:
        raise OAuthError(f"token endpoint returned status {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise OAuthError("token endpoint returned a non-JSON body") from exc

    token = payload.get("access_token")
    if not token:
        raise OAuthError("token endpoint returned no access_token")

    try:
        ttl = int(payload.get("expires_in") or _DEFAULT_TTL)
    except (TypeError, ValueError):
        ttl = _DEFAULT_TTL
    return token, time.monotonic() + max(ttl - _EXPIRY_SKEW, 0)


def get_token(endpoint, *, force_refresh: bool = False) -> str:
    key = _key(endpoint)
    if not force_refresh:
        with _lock:
            cached = _cache.get(key)
        if cached and cached[1] > time.monotonic():
            return cached[0]

    token, expires_at = _fetch(endpoint.oauth_config or {})
    with _lock:
        _cache[key] = (token, expires_at)
    logger.info("Acquired OAuth token for audit sink", endpoint_id=str(endpoint.id))
    return token


def invalidate(endpoint) -> None:
    with _lock:
        _cache.pop(_key(endpoint), None)
