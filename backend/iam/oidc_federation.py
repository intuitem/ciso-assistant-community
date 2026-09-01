import jwt
import requests
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError

from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.internal import jwtkit
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.oauth2.client import OAuth2Error

from core.net_safety import (
    BlockedRequestError,
    DnsLookupError,
    assert_public_url_unless_dev,
)

DISCOVERY_CACHE_TTL = 60 * 30
JWKS_CACHE_TTL = 60 * 30
JWKS_REFRESH_LOCK_TTL = 5
# Same default allauth's own jwtkit.lookup_kid_jwk applies when a JWK omits 'alg' RFC 7517
DEFAULT_JWK_ALG = "RS256"
REQUEST_TIMEOUT = 10

WELL_KNOWN_SUFFIX = "/.well-known/openid-configuration"


def social_app_discovery_url(social_app: SocialApp) -> str:
    url = social_app.settings["server_url"]
    if "/.well-known/" not in url:
        url = url.rstrip("/") + WELL_KNOWN_SUFFIX
    return url


def get_openid_config(discovery_url: str) -> dict:
    cache_key = f"iam:oidc-discovery:{discovery_url}"
    config = cache.get(cache_key)
    if config is None:
        assert_public_url_unless_dev(discovery_url)
        with get_adapter().get_requests_session() as sess:
            response = sess.get(discovery_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            config = response.json()
        cache.set(cache_key, config, DISCOVERY_CACHE_TTL)
    return config


def resolve_social_app_provider_config(social_app: SocialApp) -> dict:
    config = get_openid_config(social_app_discovery_url(social_app))
    return {"issuer": config["issuer"], "jwks_uri": config["jwks_uri"]}


def _fetch_and_cache_keys(cache_key: str, keys_url: str) -> dict:
    # Guarded at every fetch, not just registration: the jwks_uri comes from
    # the discovery document the remote server returns, not from the admin.
    assert_public_url_unless_dev(keys_url)
    with get_adapter().get_requests_session() as sess:
        response = sess.get(keys_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        keys_data = response.json()
    cache.set(cache_key, keys_data, JWKS_CACHE_TTL)
    return keys_data


def _cached_fetch_key(credential: str, keys_url: str, lookup):
    header = jwt.get_unverified_header(credential)
    kid = header["kid"]
    cache_key = f"iam:oidc-jwks:{keys_url}"
    refresh_lock_key = f"iam:oidc-jwks-refresh-lock:{keys_url}"
    keys_data = cache.get(cache_key)
    if keys_data is None:
        keys_data = _fetch_and_cache_keys(cache_key, keys_url)
    key = lookup(keys_data, kid)
    if not key and cache.add(refresh_lock_key, True, JWKS_REFRESH_LOCK_TTL):
        keys_data = _fetch_and_cache_keys(cache_key, keys_url)
        key = lookup(keys_data, kid)
    if not key:
        raise OAuth2Error(f"Invalid 'kid': '{kid}'")
    jwk_alg = next(
        (
            k.get("alg", DEFAULT_JWK_ALG)
            for k in keys_data.get("keys", [])
            if k.get("kid") == kid
        ),
        None,
    )
    if not jwk_alg or header.get("alg") != jwk_alg:
        raise OAuth2Error("Token 'alg' does not match the registered key's algorithm")
    return jwk_alg, key


def verify_and_decode_cached(
    *, credential: str, keys_url: str, issuer: str, audience
) -> dict:
    try:
        alg, key = _cached_fetch_key(credential, keys_url, jwtkit.lookup_kid_jwk)
        data = jwt.decode(
            credential,
            key=key,
            options={
                "verify_signature": True,
                "verify_iss": True,
                "verify_aud": True,
                "verify_exp": True,
                "require": ["exp", "iss", "aud"],
            },
            issuer=issuer,
            audience=audience,
            algorithms=[alg],
        )
        return data
    except jwt.PyJWTError as e:
        raise OAuth2Error("Invalid id_token") from e


def check_social_app_live(social_app: SocialApp) -> None:
    jwks_uri = resolve_social_app_provider_config(social_app)["jwks_uri"]
    _fetch_and_cache_keys(f"iam:oidc-jwks:{jwks_uri}", jwks_uri)


def register_social_app(
    *, name: str, provider_id: str, client_id: str, server_url: str
) -> SocialApp:
    if SocialApp.objects.filter(provider_id=provider_id).exists():
        raise DjangoValidationError(
            f"An identity provider with provider ID '{provider_id}' already exists."
        )
    if SocialApp.objects.filter(client_id=client_id).exists():
        raise DjangoValidationError(
            f"An identity provider with client ID '{client_id}' already exists."
        )
    social_app = SocialApp(
        provider="openid_connect",
        name=name,
        provider_id=provider_id,
        client_id=client_id,
        settings={"server_url": server_url},
    )
    try:
        check_social_app_live(social_app)
    except (
        requests.RequestException,
        KeyError,
        BlockedRequestError,
        DnsLookupError,
    ) as e:
        raise DjangoValidationError(
            f"Could not verify the identity provider: {e}"
        ) from e
    social_app.save()
    return social_app


def update_social_app(
    social_app: SocialApp,
    *,
    name: str | None = None,
    provider_id: str | None = None,
    client_id: str | None = None,
    server_url: str | None = None,
) -> SocialApp:
    if provider_id is not None and provider_id != social_app.provider_id:
        if (
            SocialApp.objects.filter(provider_id=provider_id)
            .exclude(pk=social_app.pk)
            .exists()
        ):
            raise DjangoValidationError(
                f"An identity provider with provider ID '{provider_id}' already exists."
            )
        social_app.provider_id = provider_id
    if name is not None:
        social_app.name = name
    connection_changed = False
    if client_id is not None and client_id != social_app.client_id:
        if (
            SocialApp.objects.filter(client_id=client_id)
            .exclude(pk=social_app.pk)
            .exists()
        ):
            raise DjangoValidationError(
                f"An identity provider with client ID '{client_id}' already exists."
            )
        social_app.client_id = client_id
        connection_changed = True
    if server_url is not None and server_url != social_app.settings.get("server_url"):
        social_app.settings["server_url"] = server_url
        connection_changed = True
    if connection_changed:
        try:
            check_social_app_live(social_app)
        except (
            requests.RequestException,
            KeyError,
            BlockedRequestError,
            DnsLookupError,
        ) as e:
            raise DjangoValidationError(
                f"Could not verify the identity provider: {e}"
            ) from e
    social_app.save()
    return social_app


__all__ = [
    "check_social_app_live",
    "register_social_app",
    "resolve_social_app_provider_config",
    "social_app_discovery_url",
    "update_social_app",
    "verify_and_decode_cached",
]
