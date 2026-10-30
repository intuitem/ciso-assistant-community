"""Single Logout helpers for SSO sessions."""

from importlib import import_module
from urllib.parse import urlencode

import structlog
from allauth.socialaccount.providers.saml.utils import (
    build_saml_config,
    prepare_django_request,
)
from django.conf import settings
from django.contrib.auth import SESSION_KEY as AUTH_USER_SESSION_KEY
from django.http import HttpRequest
from django.urls import reverse
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from rest_framework import permissions, views
from rest_framework.response import Response

from iam.sso.models import SSOSettings

logger = structlog.get_logger(__name__)

SLO_SESSION_KEY = "sso_slo_state"
SLO_OWNER_SESSION_KEY = "sso_slo_owner"
ALLAUTH_SESSION_LABEL = "allauth_session_token"
# The callback session only has to survive until the frontend hands its state
# over to the allauth session, so it must not linger for SESSION_COOKIE_AGE.
CALLBACK_SESSION_TTL = 600


def _get_session_store(session_key: str):
    engine = import_module(settings.SESSION_ENGINE)
    return engine.SessionStore(session_key=session_key)


def _session_owner_pk(session) -> str | None:
    """The user a session belongs to, or None when it belongs to nobody.

    The SAML callback session holds no Django login, so `finish_acs` stamps the
    owner next to the SLO state; OIDC and allauth sessions carry the usual
    `_auth_user_id`.
    """
    return session.get(AUTH_USER_SESSION_KEY) or session.get(SLO_OWNER_SESSION_KEY)


def _public_url(path: str) -> str:
    return f"{settings.CISO_ASSISTANT_URL.rstrip('/')}{path}"


def get_post_logout_redirect_url() -> str:
    return _public_url("/login")


def copy_slo_state_from_session_key(
    request: HttpRequest, source_session_key: str | None
) -> None:
    """Copy SLO state from the callback session into the allauth session.

    The caller must own the source session, so a leaked session key cannot be
    used to lift someone else's SLO material into one's own session.
    """
    if not source_session_key or request.session.get(SLO_SESSION_KEY):
        return
    if source_session_key == request.session.session_key:
        return
    if not request.user.is_authenticated:
        return
    source_session = _get_session_store(source_session_key)
    if _session_owner_pk(source_session) != str(request.user.pk):
        logger.warning("Callback session does not belong to the caller, ignoring it")
        return
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
    request.session.set_expiry(CALLBACK_SESSION_TTL)
    logger.info("Stashed OIDC single logout state in session")


def stash_saml_slo_state(request: HttpRequest, auth, user) -> None:
    """Keep the SAML session identifiers needed for SP-initiated logout.

    `finish_acs` performs no Django login, so the owner is stamped explicitly.
    """
    request.session[SLO_OWNER_SESSION_KEY] = str(user.pk)
    request.session[SLO_SESSION_KEY] = {
        "provider": "saml",
        "name_id": auth.get_nameid(),
        "session_index": auth.get_session_index(),
        "name_id_format": auth.get_nameid_format(),
        "name_id_nq": auth.get_nameid_nq(),
        "name_id_spnq": auth.get_nameid_spnq(),
    }
    request.session.set_expiry(CALLBACK_SESSION_TTL)
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


def pop_slo_state_from_sessions(
    session_keys: dict[str, str | None], owner_pk
) -> tuple[dict | None, set[str]]:
    """Destroy the caller's sessions named in `session_keys`, returning the
    first SLO state found and the labels actually destroyed.

    Every session must die server-side, whichever one yielded the SLO state:
    deleting only its cookie would leave the key replayable until expiry.
    Sessions that do not belong to `owner_pk` are left untouched, so a caller
    cannot log someone else out or read their SLO material by guessing a key.
    """
    destroyed = set()
    slo_state = None
    for label, session_key in session_keys.items():
        if not session_key:
            logger.info("No session key supplied", session=label)
            continue
        session = _get_session_store(session_key)
        if not session.exists(session_key):
            logger.info("Session not found, nothing to destroy", session=label)
            continue
        if _session_owner_pk(session) != str(owner_pk):
            logger.warning(
                "Session does not belong to the caller, leaving it untouched",
                session=label,
            )
            continue
        state = session.get(SLO_SESSION_KEY)
        session.delete(session_key)
        destroyed.add(label)
        if state and not slo_state:
            logger.info("Recovered single logout state from session", session=label)
            slo_state = state
    return slo_state, destroyed


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


class IdPLogoutURLView(views.APIView):
    """Resolve the IdP logout URL without sending the browser to the API.

    The SvelteKit BFF calls this server-side and redirects the browser itself,
    so SSO logout keeps working on deployments where the API is IP-restricted.
    Session keys travel as headers because the API cookies are not forwarded.
    `logout_url` is null when no IdP round-trip is needed, and
    `allauth_session_ended` tells the caller whether it still has to end that
    session itself.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        slo_state, destroyed = pop_slo_state_from_sessions(
            {
                ALLAUTH_SESSION_LABEL: request.META.get("HTTP_X_ALLAUTH_SESSION_TOKEN"),
                "sso_session_key": request.META.get("HTTP_X_SSO_SESSION_KEY"),
            },
            owner_pk=request.user.pk,
        )
        return Response(
            {
                "logout_url": build_idp_logout_url(request, slo_state),
                "allauth_session_ended": ALLAUTH_SESSION_LABEL in destroyed,
            }
        )
