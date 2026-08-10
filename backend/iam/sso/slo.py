"""Single Logout helpers for SSO sessions."""

from importlib import import_module
from urllib.parse import urlencode

import structlog
from allauth.socialaccount.providers.saml.views import build_auth
from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.http import HttpRequest, HttpResponseRedirect
from django.views import View

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


def _build_saml_logout_url(request, provider, slo_state) -> str | None:
    auth = build_auth(request, provider)
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
    token_state = _pop_allauth_token_session(request)
    return slo_state or token_state


def _pop_allauth_token_session(request: HttpRequest) -> dict | None:
    """Delete the allauth headless session referenced by the session-token
    cookie, returning any SLO state it held."""
    session_token = request.COOKIES.get(ALLAUTH_SESSION_TOKEN_COOKIE_NAME)
    if not session_token or session_token == request.session.session_key:
        return None

    token_session = _get_session_store(session_token)
    slo_state = token_session.get(SLO_SESSION_KEY)
    token_session.delete(session_token)
    if slo_state:
        logger.info("Recovered single logout state from allauth session token")
    return slo_state


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
        fallback = get_post_logout_redirect_url()
        slo_state = _pop_slo_state(request)
        auth_logout(request)
        if not slo_state:
            logger.info(
                "No single logout state in session, skipping IdP logout",
                had_session_cookie=settings.SESSION_COOKIE_NAME in request.COOKIES,
            )
            return _redirect_with_logout_cookies(fallback)
        try:
            sso_settings = SSOSettings.objects.get()
            if not sso_settings.slo_enabled:
                logger.info(
                    "Service provider-initiated single logout disabled, "
                    "skipping IdP logout",
                    provider=slo_state.get("provider"),
                )
                return _redirect_with_logout_cookies(fallback)
            if sso_settings.provider != slo_state.get("provider"):
                logger.warning(
                    "SSO provider changed since login, skipping IdP logout",
                    stashed_provider=slo_state.get("provider"),
                    current_provider=sso_settings.provider,
                )
                return _redirect_with_logout_cookies(fallback)
            provider = sso_settings.get_provider(request)
            logout_url = None
            if slo_state["provider"] == "openid_connect":
                logout_url = _build_oidc_logout_url(request, provider, slo_state)
            elif slo_state["provider"] == "saml":
                logout_url = _build_saml_logout_url(request, provider, slo_state)
            if logout_url:
                logger.info(
                    "Redirecting browser to IdP single logout",
                    provider=slo_state["provider"],
                )
                return _redirect_with_logout_cookies(logout_url)
            logger.warning(
                "No IdP logout URL available, skipping IdP logout",
                provider=slo_state["provider"],
            )
        except Exception as e:
            logger.error("IdP single logout failed", exc_info=e)
        return _redirect_with_logout_cookies(fallback)
