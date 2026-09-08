"""Single Logout helpers for SSO sessions."""

from importlib import import_module
from urllib.parse import urlencode

import structlog
from allauth.socialaccount.providers.saml.utils import (
    build_saml_config,
    prepare_django_request,
)
from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from django.views import View
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from rest_framework import permissions, views
from rest_framework.response import Response

from iam.sso.models import SSOSettings

logger = structlog.get_logger(__name__)

SLO_SESSION_KEY = "sso_slo_state"
ALLAUTH_SESSION_TOKEN_COOKIE_NAME = "allauth_session_token"


def _get_session_store(session_key: str):
    engine = import_module(settings.SESSION_ENGINE)
    return engine.SessionStore(session_key=session_key)


def get_post_logout_redirect_url() -> str:
    return f"{settings.CISO_ASSISTANT_URL}/login"


def copy_slo_state_from_session_key(
    request: HttpRequest, source_session_key: str | None
) -> None:
    """Copy SLO state from the callback session into the allauth session."""
    if not source_session_key or request.session.get(SLO_SESSION_KEY):
        return
    if source_session_key == request.session.session_key:
        return
    source_session = _get_session_store(source_session_key)
    slo_state = source_session.get(SLO_SESSION_KEY)
    if not slo_state:
        return
    request.session[SLO_SESSION_KEY] = slo_state
    logger.info("Copied single logout state into allauth session")


def stash_oidc_slo_state(request: HttpRequest, id_token: str | None) -> None:
    """Keep the raw id_token so logout can pass it as `id_token_hint`."""
    if not id_token:
        return
    request.session[SLO_SESSION_KEY] = {
        "provider": "openid_connect",
        "id_token": id_token,
    }
    logger.info("Stashed OIDC single logout state in session")


def stash_saml_slo_state(request: HttpRequest, auth) -> None:
    """Keep the SAML session identifiers needed for SP-initiated logout."""
    request.session[SLO_SESSION_KEY] = {
        "provider": "saml",
        "name_id": auth.get_nameid(),
        "session_index": auth.get_session_index(),
        "name_id_format": auth.get_nameid_format(),
        "name_id_nq": auth.get_nameid_nq(),
        "name_id_spnq": auth.get_nameid_spnq(),
    }
    logger.info("Stashed SAML single logout state in session")


def _build_oidc_logout_url(request, provider, slo_state) -> str | None:
    app = provider.app
    end_session_endpoint = app.settings.get("end_session_endpoint")
    if not end_session_endpoint:
        oauth2_adapter = provider.get_oauth2_adapter(request)
        end_session_endpoint = oauth2_adapter.openid_config.get("end_session_endpoint")
    if not end_session_endpoint:
        return None
    params = {
        "client_id": app.client_id,
        "post_logout_redirect_uri": get_post_logout_redirect_url(),
    }
    id_token = slo_state.get("id_token")
    if id_token:
        params["id_token_hint"] = id_token
    return f"{end_session_endpoint}?{urlencode(params)}"


def _public_url(path: str) -> str:
    return f"{settings.CISO_ASSISTANT_URL.rstrip('/')}{path}"


def _build_public_saml_config(request, provider) -> dict:
    """Build the SAML config with the SP URLs anchored on the public URL.

    allauth derives them from the request host, which is the internal one on
    BFF-issued calls; python3-saml then rejects the whole config.
    """
    org = provider.app.client_id
    config = build_saml_config(request, provider.app.settings, org)
    config["sp"]["assertionConsumerService"]["url"] = _public_url(
        reverse("saml_acs", args=[org])
    )
    config["sp"]["singleLogoutService"]["url"] = _public_url(
        reverse("saml_sls", args=[org])
    )
    if not provider.app.settings.get("sp", {}).get("entity_id"):
        config["sp"]["entityId"] = _public_url(reverse("saml_metadata", args=[org]))
    return config


def _build_saml_logout_url(request, provider, slo_state) -> str | None:
    auth = OneLogin_Saml2_Auth(
        prepare_django_request(request), _build_public_saml_config(request, provider)
    )
    return auth.logout(
        return_to=get_post_logout_redirect_url(),
        name_id=slo_state.get("name_id"),
        session_index=slo_state.get("session_index"),
        nq=slo_state.get("name_id_nq"),
        name_id_format=slo_state.get("name_id_format"),
        spnq=slo_state.get("name_id_spnq"),
    )


def _pop_slo_state(request: HttpRequest) -> dict | None:
    slo_state = request.session.pop(SLO_SESSION_KEY, None)
    # The allauth headless session must die server-side no matter which
    # session yielded the SLO state — deleting only its cookie would leave
    # the session token replayable until expiry.
    token_state = pop_slo_state_from_sessions(
        [request.COOKIES.get(ALLAUTH_SESSION_TOKEN_COOKIE_NAME)],
        skip_session_key=request.session.session_key,
    )
    return slo_state or token_state


def pop_slo_state_from_sessions(
    session_keys, skip_session_key: str | None = None
) -> dict | None:
    """Destroy the given sessions, returning the first SLO state found."""
    slo_state = None
    for session_key in session_keys:
        if not session_key or session_key == skip_session_key:
            continue
        session = _get_session_store(session_key)
        state = session.get(SLO_SESSION_KEY)
        session.delete(session_key)
        if state and not slo_state:
            logger.info("Recovered single logout state from session")
            slo_state = state
    return slo_state


def build_idp_logout_url(request: HttpRequest, slo_state: dict | None) -> str | None:
    """Return the IdP logout URL for a stashed SLO state, None to skip SLO."""
    if not slo_state:
        logger.info("No single logout state in session, skipping IdP logout")
        return None
    try:
        sso_settings = SSOSettings.objects.get()
        if not sso_settings.slo_enabled:
            logger.info(
                "Service provider-initiated single logout disabled, "
                "skipping IdP logout",
                provider=slo_state.get("provider"),
            )
            return None
        if sso_settings.provider != slo_state.get("provider"):
            logger.warning(
                "SSO provider changed since login, skipping IdP logout",
                stashed_provider=slo_state.get("provider"),
                current_provider=sso_settings.provider,
            )
            return None
        provider = sso_settings.get_provider(request)
        logout_url = None
        if slo_state["provider"] == "openid_connect":
            logout_url = _build_oidc_logout_url(request, provider, slo_state)
        elif slo_state["provider"] == "saml":
            logout_url = _build_saml_logout_url(request, provider, slo_state)
        if logout_url:
            logger.info(
                "Resolved IdP single logout URL",
                provider=slo_state["provider"],
            )
            return logout_url
        logger.warning(
            "No IdP logout URL available, skipping IdP logout",
            provider=slo_state["provider"],
        )
    except Exception as e:
        logger.error("IdP single logout failed", exc_info=e)
    return None


def _redirect_with_logout_cookies(url: str) -> HttpResponseRedirect:
    # token and allauth_session_token are set host-only with path=/ (frontend
    # and OIDC/SAML callback views); deletion must match those attributes.
    response = HttpResponseRedirect(url)
    response.delete_cookie("token", path="/", samesite="Lax")
    response.delete_cookie(ALLAUTH_SESSION_TOKEN_COOKIE_NAME, path="/", samesite="Lax")
    return response


class IdPLogoutView(View):
    """Redirect the browser through the IdP logout endpoint.

    Deliberately a plain GET without CSRF protection: it is the target of a
    cross-request redirect chain and, for SAML, of the IdP round-trip. The
    worst a forged request can do is log the user out (no state is disclosed
    and the IdP redirect only ever targets the configured provider).
    """

    def get(self, request):
        slo_state = _pop_slo_state(request)
        auth_logout(request)
        logout_url = build_idp_logout_url(request, slo_state)
        return _redirect_with_logout_cookies(
            logout_url or get_post_logout_redirect_url()
        )


class IdPLogoutURLView(views.APIView):
    """Resolve the IdP logout URL without sending the browser to the API.

    The SvelteKit BFF calls this server-side and redirects the browser itself,
    so SSO logout keeps working on deployments where the API is IP-restricted.
    Session keys travel as headers because the API cookies are not forwarded.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        slo_state = pop_slo_state_from_sessions(
            [
                request.META.get("HTTP_X_ALLAUTH_SESSION_TOKEN"),
                request.META.get("HTTP_X_SSO_SESSION_KEY"),
            ]
        )
        logout_url = build_idp_logout_url(request, slo_state)
        return Response({"logout_url": logout_url or get_post_logout_redirect_url()})
