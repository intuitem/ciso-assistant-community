import secrets
import string
import structlog
from allauth.account.internal.decorators import login_not_required  # type: ignore[import-untyped]
from allauth.account.utils import get_next_redirect_url  # type: ignore[import-untyped]
from allauth.socialaccount.adapter import get_adapter as get_socialaccount_adapter  # type: ignore[import-untyped]
from allauth.socialaccount.helpers import render_authentication_error  # type: ignore[import-untyped]
from allauth.socialaccount.models import SocialApp  # type: ignore[import-untyped]
from allauth.socialaccount.providers.base.constants import (  # type: ignore[import-untyped]
    AuthAction,
    AuthProcess,
)
from allauth.socialaccount.providers.oauth2.client import OAuth2Error  # type: ignore[import-untyped]
from allauth.socialaccount.providers.oauth2.views import (  # type: ignore[import-untyped]
    OAuth2CallbackView,
)
from allauth.socialaccount.providers.openid_connect.views import (  # type: ignore[import-untyped]
    OpenIDConnectOAuth2Adapter,
)
from allauth.utils import get_request_param  # type: ignore[import-untyped]
from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponseRedirect
from urllib.parse import urlparse

from iam.sso.errors import AuthError
from iam.utils import generate_token

logger = structlog.get_logger(__name__)

# State and nonce parameters. allauth's default state is 16 chars and sends no
# nonce. We generate both from this alphabet at a length that satisfies the
# OIDC-standard `^[A-Za-z0-9-._~,]{36,128}$` form.
_OIDC_TOKEN_ALPHABET = string.ascii_letters + string.digits + "-._~,"
_OIDC_TOKEN_LENGTH = 40
_OIDC_NONCE_SESSION_PREFIX = "oidc_nonce::"
# Cap stashed nonces per session so abandoned login attempts can't grow the
# session bag indefinitely. Mirrors allauth's MAX_STATES (statekit.py).
_OIDC_NONCE_SESSION_MAX = 10


def _generate_oidc_token(length: int = _OIDC_TOKEN_LENGTH) -> str:
    return "".join(secrets.choice(_OIDC_TOKEN_ALPHABET) for _ in range(length))


class NonceValidatingOpenIDConnectAdapter(OpenIDConnectOAuth2Adapter):
    """OIDC adapter that validates the id_token `nonce` claim against the value
    stashed at the start of the authorization flow. Validation is lenient: a
    nonce that is present must match, but an id_token that omits the nonce
    claim only logs a warning so non-conformant IdPs are not broken."""

    def complete_login(self, request, app, token, **kwargs):
        id_token_str = kwargs["response"].get("id_token")
        fetch_userinfo = app.settings.get("fetch_userinfo", True)

        data = {}
        if fetch_userinfo or (not id_token_str):
            data["userinfo"] = self._fetch_user_info(token.token)
        if id_token_str:
            decoded = self._decode_id_token(app, id_token_str)
            state_id = get_request_param(request, "state")
            expected_nonce = request.session.pop(
                f"{_OIDC_NONCE_SESSION_PREFIX}{state_id}", None
            )
            if expected_nonce is not None:
                returned_nonce = decoded.get("nonce")
                if returned_nonce is None:
                    logger.warning(
                        "OIDC id_token has no nonce claim; skipping nonce validation",
                        provider=self.provider_id,
                    )
                elif returned_nonce != expected_nonce:
                    logger.error(
                        "OIDC nonce mismatch",
                        provider=self.provider_id,
                    )
                    raise OAuth2Error("OIDC nonce mismatch")
            logger.debug(
                "OIDC id_token decoded and nonce validated",
                provider=self.provider_id,
            )
            data["id_token"] = decoded
        return self.get_provider().sociallogin_from_response(request, data)


def oidc_redirect(
    request: HttpRequest,
    provider,
    *,
    process: str | None = None,
    next_url: str | None = None,
    **state_kwargs,
) -> HttpResponseRedirect:
    """Builds the authorization redirect mirroring `OAuth2Provider.redirect`,
    but with a state_id and nonce that match the OIDC-standard regex
    `^[A-Za-z0-9-._~,]{36,128}$`. The nonce is stashed in the session so the
    callback adapter can verify it against the id_token claim. Extra
    `state_kwargs` (e.g. `headless=True`) are forwarded to allauth's state
    stash so downstream flow behavior is preserved."""
    app = provider.app
    oauth2_adapter = provider.get_oauth2_adapter(request)
    client = oauth2_adapter.get_client(request, app)

    if next_url is None:
        next_url = get_next_redirect_url(request)
    if process is None:
        process = get_request_param(request, "process", AuthProcess.LOGIN)
    action = request.GET.get("action", AuthAction.AUTHENTICATE)
    auth_params = provider.get_auth_params_from_request(request, action)
    pkce_params = provider.get_pkce_params()
    code_verifier = pkce_params.pop("code_verifier", None)
    auth_params.update(pkce_params)

    scope = provider.get_scope_from_request(request)

    state_id = _generate_oidc_token()
    nonce = _generate_oidc_token()
    auth_params["nonce"] = nonce

    provider.stash_redirect_state(
        request,
        process,
        next_url,
        data=None,
        state_id=state_id,
        pkce_code_verifier=code_verifier,
        **state_kwargs,
    )
    # Out-of-band: state is consumed by allauth before complete_login runs,
    # so we key the expected nonce by state_id in a separate session entry.
    _stash_oidc_nonce(request, state_id, nonce)

    client.state = state_id
    return HttpResponseRedirect(
        client.get_redirect_url(oauth2_adapter.authorize_url, scope, auth_params)
    )


def _stash_oidc_nonce(request: HttpRequest, state_id: str, nonce: str) -> None:
    """Stash the expected nonce for `state_id` and evict oldest entries past
    the cap so abandoned login attempts can't grow the session indefinitely."""
    stale_keys = [
        k for k in request.session.keys() if k.startswith(_OIDC_NONCE_SESSION_PREFIX)
    ]
    overflow = len(stale_keys) - _OIDC_NONCE_SESSION_MAX + 1
    if overflow > 0:
        for key in stale_keys[:overflow]:
            request.session.pop(key, None)
    request.session[f"{_OIDC_NONCE_SESSION_PREFIX}{state_id}"] = nonce


@login_not_required
def callback(request, provider_id):
    logger.debug(
        "OIDC callback initiated",
        provider=provider_id,
        method=request.method,
        has_code=bool(request.GET.get("code")),
        has_state=bool(request.GET.get("state")),
        has_error=bool(request.GET.get("error")),
        query_params=list(request.GET.keys()),
    )

    # Log error from provider if present
    if request.GET.get("error"):
        logger.error(
            "OIDC provider returned error",
            provider=provider_id,
            error=request.GET.get("error"),
            error_description=request.GET.get("error_description"),
            error_uri=request.GET.get("error_uri"),
        )

    try:
        logger.debug(
            "Creating OIDC adapter",
            provider=provider_id,
            user_authenticated=not request.user.is_anonymous,
        )

        response = OAuth2CallbackView.adapter_view(
            NonceValidatingOpenIDConnectAdapter(request, provider_id)
        )(request)

        logger.debug(
            "OIDC adapter response received",
            provider=provider_id,
            status_code=response.status_code,
            has_location_header=bool(response.get("Location")),
            user_authenticated=not request.user.is_anonymous,
        )

        if response.status_code != 302:
            logger.warning(
                "OIDC callback returned non-redirect status",
                provider=provider_id,
                status_code=response.status_code,
                content_type=response.get("Content-Type"),
            )
            return response

        if request.user.is_anonymous:
            logger.error(
                "SSO authentication failed - user is anonymous after callback",
                provider=provider_id,
                has_socialaccount_state=bool(
                    request.session.get("socialaccount_state")
                ),
            )
            return render_authentication_error(
                request, None, error=AuthError.FAILED_SSO
            )

        token = generate_token(request.user)
        next = f"{settings.CISO_ASSISTANT_URL.rstrip('/')}/sso/authenticate"

        logger.info(
            "SSO authentication successful",
            provider=provider_id,
        )

        response = HttpResponseRedirect(next)
        response.set_cookie(
            "token",
            token,
            httponly=True,
            secure=settings.CISO_ASSISTANT_URL.startswith("https"),
            samesite="Lax",
            path="/",
        )
        return response
    except SocialApp.DoesNotExist as e:
        logger.error(
            "OIDC provider configuration not found",
            provider=provider_id,
            error=str(e),
            exc_info=True,
        )
        raise Http404 from e
    except Exception as e:
        logger.error(
            "OIDC callback error - unexpected exception",
            provider=provider_id,
            error_type=type(e).__name__,
            error_message=str(e),
            user_authenticated=not request.user.is_anonymous,
            has_code=bool(request.GET.get("code")),
            has_state=bool(request.GET.get("state")),
            exc_info=True,
        )
        return render_authentication_error(request, None, error=AuthError.FAILED_SSO)


@login_not_required
def login(request, provider_id):
    # Sanitize referer to only log origin (domain), removing paths and query params
    referer = request.META.get("HTTP_REFERER")
    referer_origin = None
    if referer:
        try:
            parsed = urlparse(referer)
            referer_origin = (
                f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else None
            )
        except Exception:
            referer_origin = None

    logger.debug(
        "OIDC login initiated",
        provider=provider_id,
        method=request.method,
        user_authenticated=not request.user.is_anonymous,
        referer_origin=referer_origin,
    )

    try:
        logger.debug(
            "Creating OIDC login adapter",
            provider=provider_id,
        )

        provider = get_socialaccount_adapter().get_provider(request, provider_id)
        response = oidc_redirect(request, provider)

        logger.debug(
            "OIDC login redirect prepared",
            provider=provider_id,
            status_code=response.status_code,
            has_location=bool(response.get("Location")),
            location_domain=response.get("Location", "").split("?")[0]
            if response.get("Location")
            else None,
        )

        return response
    except SocialApp.DoesNotExist:
        logger.error(
            "OIDC provider configuration not found",
            provider=provider_id,
            available_providers="Check SocialApp configuration in Django admin",
        )
        raise Http404
    except Exception as e:
        logger.error(
            "SSO login error - unexpected exception",
            provider=provider_id,
            error_type=type(e).__name__,
            error_message=str(e),
            user_authenticated=not request.user.is_anonymous,
            exc_info=True,
        )
        return render_authentication_error(request, None, error=AuthError.FAILED_SSO)
