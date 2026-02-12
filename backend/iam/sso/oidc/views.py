import structlog
from allauth.socialaccount.helpers import render_authentication_error  # type: ignore[import-untyped]
from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from urllib.parse import urlparse

from allauth.account.internal.decorators import login_not_required  # type: ignore[import-untyped]
from allauth.socialaccount.models import SocialApp  # type: ignore[import-untyped]
from allauth.socialaccount.providers.oauth2.views import (  # type: ignore[import-untyped]
    OAuth2CallbackView,
    OAuth2LoginView,
)
from allauth.socialaccount.providers.openid_connect.views import (  # type: ignore[import-untyped]
    OpenIDConnectOAuth2Adapter,
)

from iam.sso.errors import AuthError
from iam.utils import generate_token

logger = structlog.get_logger(__name__)


@login_not_required
def callback(request, provider_id):
    logger.info(
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
            OpenIDConnectOAuth2Adapter(request, provider_id)
        )(request)

        logger.info(
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

        logger.info(
            "Generating authentication token for user",
            provider=provider_id,
        )

        token = generate_token(request.user)
        next = f"{settings.CISO_ASSISTANT_URL.rstrip('/')}/sso/authenticate/{token}"

        logger.info(
            "SSO authentication successful - redirecting to frontend",
            provider=provider_id,
        )

        return HttpResponseRedirect(next)
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

    logger.info(
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

        view = OAuth2LoginView.adapter_view(
            OpenIDConnectOAuth2Adapter(request, provider_id)
        )
        response = view(request)

        logger.info(
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
