from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from allauth.account.internal.decorators import login_not_required
from allauth.idp.oidc.adapter import get_adapter
from allauth.idp.oidc.internal.oauthlib.server import get_server
from allauth.idp.oidc.internal.oauthlib.utils import extract_params
from allauth.idp.oidc.internal.resources import get_resources
from allauth.idp.oidc.models import Client
from allauth.idp.oidc.views import AuthorizationView
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.signing import BadSignature, Signer
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_deny
from django.views.decorators.csrf import csrf_exempt
from knox.auth import TokenAuthentication
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from rest_framework.exceptions import AuthenticationFailed

from iam.mcp_access import is_mcp_request, refusal_reason
from iam.models import ConnectedAppUse

KNOX_COOKIE = "token"


def _user_from_knox_cookie(request):
    raw = request.COOKIES.get(KNOX_COOKIE)
    if not raw:
        return None
    try:
        user, _ = TokenAuthentication().authenticate_credentials(raw.encode())
    except AuthenticationFailed:
        return None
    return user if user.is_active else None


def _with_iss(location: str, issuer: str) -> str:
    parts = urlsplit(location)
    query = parse_qsl(parts.query, keep_blank_values=True)
    if not any(key in ("code", "error") for key, _ in query):
        return location
    query.append(("iss", issuer))
    return urlunsplit(parts._replace(query=urlencode(query)))


def _pending_request(request):
    """(scopes, request info) of the authorization asked for, once its client and
    redirect_uri are valid; None otherwise, and allauth reports the error."""
    if request.method == "POST":
        try:
            return Signer().unsign_object(request.POST.get("request") or "")
        except BadSignature:
            return None
    try:
        scopes, info = get_server().validate_authorization_request(
            *extract_params(request)
        )
        info["resources"] = get_resources(request)
    except OAuth2Error, ValidationError:
        return None
    return scopes, info


def _access_denied_url(info) -> str | None:
    redirect_uri = info.get("redirect_uri")
    if not redirect_uri:
        return None
    parts = urlsplit(redirect_uri)
    query = parse_qsl(parts.query, keep_blank_values=True) + [
        ("error", "access_denied")
    ]
    if info.get("state"):
        query.append(("state", info["state"]))
    query.append(("iss", get_adapter().get_issuer()))
    return urlunsplit(parts._replace(query=urlencode(query)))


# Overriding dispatch drops the decorators allauth puts on it, so restate them.
@method_decorator(xframe_options_deny, name="dispatch")
@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(login_not_required, name="dispatch")
class CISOAuthorizationView(AuthorizationView):
    """
    The frontend logs users in headlessly with a Knox token kept in a cookie on
    the same host, so there is no Django session for allauth to see. Accept that
    cookie here, and only here: honouring it API-wide would open a CSRF hole.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            user = _user_from_knox_cookie(request)
            if user is not None:
                request.user = user
        # before allauth: prompt=none and skip-consent clients get a code without
        # ever showing the consent page
        if request.user.is_authenticated:
            refusal = self._refusal(request)
            if refusal is not None:
                return refusal
        response = super().dispatch(request, *args, **kwargs)
        location = response.get("Location") if response.status_code == 302 else None
        # absolute Location = going back to the client (RFC 9207)
        if location and urlsplit(location).scheme:
            response["Location"] = _with_iss(location, get_adapter().get_issuer())
        return response

    def _refusal(self, request):
        pending = _pending_request(request)
        if pending is None:
            return None
        scopes, info = pending
        reason = refusal_reason(
            request.user, is_mcp_request(scopes, info.get("resources"))
        )
        if reason is None:
            return None
        return render(
            request,
            "idp/oidc/authorization_refused.html",
            {
                "reason": reason,
                "client": Client.objects.filter(id=info.get("client_id")).first(),
                "back_url": _access_denied_url(info),
            },
            status=403,
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        location = response.get("Location") or ""
        if any(key == "code" for key, _ in parse_qsl(urlsplit(location).query)):
            ConnectedAppUse.record_authorization(
                self.request.user.pk, self._request_info["client_id"]
            )
        return response

    def _login_required(self, request):
        # prompt=login is ignored: allauth's handler redirects to account_login,
        # which does not exist with HEADLESS_ONLY, and erroring back to the client
        # here would happen before redirect_uri is validated.
        prompts = (request.GET.get("prompt") or "").split()
        if "none" in prompts or request.user.is_authenticated:
            return None
        login_url = settings.CISO_ASSISTANT_URL.rstrip("/") + "/login"
        return HttpResponseRedirect(
            f"{login_url}?{urlencode({'next': request.get_full_path()})}"
        )
