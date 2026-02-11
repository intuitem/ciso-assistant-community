import structlog
from allauth.socialaccount.helpers import render_authentication_error  # type: ignore[import-untyped]
from django.conf import settings
from django.http import Http404, HttpResponseRedirect

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
    try:
        response = OAuth2CallbackView.adapter_view(
            OpenIDConnectOAuth2Adapter(request, provider_id)
        )(request)
        if response.status_code != 302:
            return response
        if request.user.is_anonymous:
            logger.error("SSO authentication failed", provider=provider_id)
            return render_authentication_error(
                request, None, error=AuthError.FAILED_SSO
            )
        token = generate_token(request.user)
        next = f"{settings.CISO_ASSISTANT_URL.rstrip('/')}/sso/authenticate/{token}"
        return HttpResponseRedirect(next)
    except SocialApp.DoesNotExist as e:
        raise Http404 from e
    except Exception as e:
        logger.error("OIDC callback error", provider=provider_id, exc_info=True)
        return render_authentication_error(request, None, error=AuthError.FAILED_SSO)


@login_not_required
def login(request, provider_id):
    try:
        view = OAuth2LoginView.adapter_view(
            OpenIDConnectOAuth2Adapter(request, provider_id)
        )
        return view(request)
    except SocialApp.DoesNotExist:
        raise Http404
    except Exception as e:
        logger.error(
            "SSO login error", provider=provider_id, error=str(e), exc_info=True
        )
        return render_authentication_error(request, None, error=AuthError.FAILED_SSO)
