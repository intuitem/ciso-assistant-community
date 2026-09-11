from importlib import import_module
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.contrib.auth import SESSION_KEY as AUTH_USER_SESSION_KEY
from django.test import RequestFactory, override_settings
from knox.models import AuthToken
from rest_framework.test import APIClient

from global_settings.models import GlobalSettings
from iam.models import User
from iam.sso.slo import (
    CALLBACK_SESSION_TTL,
    SLO_OWNER_SESSION_KEY,
    SLO_SESSION_KEY,
    _build_public_saml_config,
    build_idp_logout_url,
    copy_slo_state_from_session_key,
    stash_saml_slo_state,
)

PUBLIC_URL = "https://app.example.com"
IDP_SLO_URL = "https://idp.example.com/slo"
INTERNAL_HOST = "backend:8000"
CLIENT_ID = "0"

SAML_SETTINGS = {
    "sp": {"entity_id": "ciso-assistant"},
    "idp": {
        "entity_id": "https://idp.example.com/metadata",
        "x509cert": "",
        "sso_url": "https://idp.example.com/sso",
        "slo_url": IDP_SLO_URL,
    },
    "advanced": {"allow_single_label_domains": False},
}

SLO_STATE = {
    "provider": "saml",
    "name_id": "user@example.com",
    "session_index": "_session_index",
    "name_id_format": None,
    "name_id_nq": None,
    "name_id_spnq": None,
}

test_settings = override_settings(
    CISO_ASSISTANT_URL=PUBLIC_URL,
    ALLOWED_HOSTS=["backend", "localhost", "testserver", "app.example.com"],
)


def _internal_request():
    """A logout-url call issued by the frontend server, not by the browser."""
    return RequestFactory().post("/api/iam/sso/logout-url/", HTTP_HOST=INTERNAL_HOST)


def _make_saml_sso_settings():
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.SSO,
        defaults={
            "value": {
                "is_enabled": True,
                "slo_enabled": True,
                "provider": "saml",
                "provider_id": "test-saml",
                "name": "Test SAML",
                "client_id": CLIENT_ID,
                "settings": SAML_SETTINGS,
            }
        },
    )


@test_settings
def test_saml_sp_config_uses_public_origin_on_internal_host():
    provider = SimpleNamespace(
        app=SimpleNamespace(client_id=CLIENT_ID, settings=SAML_SETTINGS)
    )

    config = _build_public_saml_config(_internal_request(), provider)

    assert (
        config["sp"]["assertionConsumerService"]["url"]
        == f"{PUBLIC_URL}/api/accounts/saml/{CLIENT_ID}/acs/"
    )
    assert (
        config["sp"]["singleLogoutService"]["url"]
        == f"{PUBLIC_URL}/api/accounts/saml/{CLIENT_ID}/sls/"
    )


@pytest.mark.django_db
@test_settings
def test_saml_logout_url_resolved_for_a_call_on_the_internal_host():
    """python3-saml rejects the internal host, which used to skip SLO silently."""
    _make_saml_sso_settings()

    logout_url = build_idp_logout_url(_internal_request(), SLO_STATE)

    assert logout_url is not None
    assert logout_url.startswith(f"{IDP_SLO_URL}?")
    assert "SAMLRequest=" in logout_url


# --- IdPLogoutURLView -------------------------------------------------------

LOGOUT_URL_ENDPOINT = "/api/iam/sso/logout-url/"


def _session_store():
    return import_module(settings.SESSION_ENGINE).SessionStore


def _make_session(user, slo_state=None) -> str:
    """A logged-in Django session for `user`, optionally holding SLO state."""
    session = _session_store()()
    session[AUTH_USER_SESSION_KEY] = str(user.pk)
    if slo_state:
        session[SLO_SESSION_KEY] = slo_state
    session.create()
    return session.session_key


def _make_saml_callback_session(user, slo_state=None) -> str:
    """The session `finish_acs` leaves behind: an owner stamp, no Django login."""
    session = _session_store()()
    session[SLO_OWNER_SESSION_KEY] = str(user.pk)
    if slo_state:
        session[SLO_SESSION_KEY] = slo_state
    session.create()
    return session.session_key


def _session_exists(session_key: str) -> bool:
    return _session_store()(session_key=session_key).exists(session_key)


def _client_for(user) -> APIClient:
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.fixture
def sso_user(db):
    return User.objects.create_user(email="sso@example.com")


@pytest.mark.django_db
@test_settings
def test_logout_url_view_resolves_idp_url_and_destroys_both_sessions(sso_user):
    _make_saml_sso_settings()
    allauth_key = _make_session(sso_user, SLO_STATE)
    callback_key = _make_session(sso_user, SLO_STATE)

    res = _client_for(sso_user).post(
        LOGOUT_URL_ENDPOINT,
        HTTP_HOST=INTERNAL_HOST,
        HTTP_X_ALLAUTH_SESSION_TOKEN=allauth_key,
        HTTP_X_SSO_SESSION_KEY=callback_key,
    )

    assert res.status_code == 200
    assert res.json()["logout_url"].startswith(f"{IDP_SLO_URL}?")
    assert res.json()["allauth_session_ended"] is True
    assert not _session_exists(allauth_key)
    assert not _session_exists(callback_key)


@pytest.mark.django_db
@test_settings
def test_logout_url_view_returns_null_when_no_slo_state(sso_user):
    _make_saml_sso_settings()
    allauth_key = _make_session(sso_user)

    res = _client_for(sso_user).post(
        LOGOUT_URL_ENDPOINT,
        HTTP_HOST=INTERNAL_HOST,
        HTTP_X_ALLAUTH_SESSION_TOKEN=allauth_key,
    )

    assert res.status_code == 200
    assert res.json() == {"logout_url": None, "allauth_session_ended": True}
    assert not _session_exists(allauth_key)


@pytest.mark.django_db
@test_settings
def test_logout_url_view_accepts_the_saml_callback_session(sso_user):
    """`finish_acs` performs no Django login, so the callback session is owned
    through its stamp only."""
    _make_saml_sso_settings()
    callback_key = _make_saml_callback_session(sso_user, SLO_STATE)

    res = _client_for(sso_user).post(
        LOGOUT_URL_ENDPOINT,
        HTTP_HOST=INTERNAL_HOST,
        HTTP_X_SSO_SESSION_KEY=callback_key,
    )

    assert res.status_code == 200
    assert res.json()["logout_url"].startswith(f"{IDP_SLO_URL}?")
    assert res.json()["allauth_session_ended"] is False
    assert not _session_exists(callback_key)


@pytest.mark.django_db
@test_settings
def test_logout_url_view_ignores_sessions_of_other_users(sso_user):
    """A leaked session key must not let a caller log its owner out or read
    their SLO material."""
    _make_saml_sso_settings()
    victim = User.objects.create_user(email="victim@example.com")
    victim_key = _make_session(victim, SLO_STATE)

    res = _client_for(sso_user).post(
        LOGOUT_URL_ENDPOINT,
        HTTP_HOST=INTERNAL_HOST,
        HTTP_X_SSO_SESSION_KEY=victim_key,
    )

    assert res.status_code == 200
    assert res.json() == {"logout_url": None, "allauth_session_ended": False}
    assert _session_exists(victim_key)


@pytest.mark.django_db
@test_settings
def test_logout_url_view_requires_authentication(sso_user):
    session_key = _make_session(sso_user, SLO_STATE)

    res = APIClient().post(
        LOGOUT_URL_ENDPOINT,
        HTTP_HOST=INTERNAL_HOST,
        HTTP_X_SSO_SESSION_KEY=session_key,
    )

    assert res.status_code == 401
    assert _session_exists(session_key)


# --- SLO state handoff ------------------------------------------------------


def _handoff_request(user):
    """A session-token call: the caller's own fresh session, plus its user."""
    request = RequestFactory().post("/api/iam/session-token/")
    session = _session_store()()
    session.create()
    request.session = session
    request.user = user
    return request


@pytest.mark.django_db
@test_settings
def test_handoff_copies_the_callers_own_callback_session(sso_user):
    callback_key = _make_saml_callback_session(sso_user, SLO_STATE)
    request = _handoff_request(sso_user)

    copy_slo_state_from_session_key(request, callback_key)

    assert request.session[SLO_SESSION_KEY] == SLO_STATE


@pytest.mark.django_db
@test_settings
def test_handoff_refuses_a_callback_session_owned_by_someone_else(sso_user):
    """A leaked session key must not let a caller lift someone else's SLO
    material into their own session."""
    victim = User.objects.create_user(email="victim2@example.com")
    victim_key = _make_saml_callback_session(victim, SLO_STATE)
    request = _handoff_request(sso_user)

    copy_slo_state_from_session_key(request, victim_key)

    assert SLO_SESSION_KEY not in request.session


@pytest.mark.django_db
@test_settings
def test_saml_stash_stamps_the_owner_and_bounds_the_session_lifetime(sso_user):
    """The callback session only carries state to the handoff, so it must not
    live for SESSION_COOKIE_AGE."""
    request = _handoff_request(sso_user)
    auth = SimpleNamespace(
        get_nameid=lambda: "user@example.com",
        get_session_index=lambda: "_session_index",
        get_nameid_format=lambda: None,
        get_nameid_nq=lambda: None,
        get_nameid_spnq=lambda: None,
    )

    stash_saml_slo_state(request, auth, sso_user)

    assert request.session[SLO_OWNER_SESSION_KEY] == str(sso_user.pk)
    assert 0 < request.session.get_expiry_age() <= CALLBACK_SESSION_TTL
