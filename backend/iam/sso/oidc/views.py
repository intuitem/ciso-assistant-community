from allauth.socialaccount.helpers import render_authentication_error
from django.conf import settings
from django.http import Http404, HttpResponseRedirect

from allauth.account.internal.decorators import login_not_required
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2CallbackView,
    OAuth2LoginView,
)
from allauth.socialaccount.providers.openid_connect.views import (
    OpenIDConnectOAuth2Adapter,
)

from iam.sso.errors import AuthError
from iam.utils import generate_token


@login_not_required
def callback(request, provider_id):
    try:
        response = OAuth2CallbackView.adapter_view(
            OpenIDConnectOAuth2Adapter(request, provider_id)
        )(request)
        if response.status_code != 302:
            return response
        if request.user.is_anonymous:
            return render_authentication_error(
                request, None, error=AuthError.FAILED_SSO
            )
        token = generate_token(request.user)
        next = f"{settings.CISO_ASSISTANT_URL.rstrip('/')}/sso/authenticate/{token}"
        return HttpResponseRedirect(next)
    except SocialApp.DoesNotExist as e:
        raise Http404 from e


@login_not_required
def login(request, provider_id):
    try:
        view = OAuth2LoginView.adapter_view(
            OpenIDConnectOAuth2Adapter(request, provider_id)
        )
        return view(request)
    except SocialApp.DoesNotExist:
        raise Http404
