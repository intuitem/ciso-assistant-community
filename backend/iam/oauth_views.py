from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from allauth.account.internal.decorators import login_not_required
from allauth.idp.oidc.adapter import get_adapter
from allauth.idp.oidc.forms import AuthorizationForm
from allauth.idp.oidc.internal.oauthlib.server import get_server
from allauth.idp.oidc.internal.oauthlib.utils import extract_params
from allauth.idp.oidc.internal.resources import get_resources
from allauth.idp.oidc.models import Client, Token
from allauth.idp.oidc.views import AuthorizationView
from allauth.idp.oidc.views import configuration as oidc_configuration
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.signing import BadSignature, Signer
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.clickjacking import xframe_options_deny
from django.views.decorators.csrf import csrf_exempt
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from rest_framework.exceptions import AuthenticationFailed

from iam.authentication import KnoxTokenAuthentication, is_self_registered
from iam.mcp_access import is_mcp_request, mcp_writes_enabled, refusal_reason
from iam.models import AppGrant, ConnectedAppUse, ConnectionProfile
from iam.oidc_adapter import MCP_SCOPES

WRITE_ACTIONS = ("create", "update", "delete")


def profile_scopes(requested, allowed) -> list[str]:
    """MCP access is one scope; what the app may do comes from its profile."""
    scopes = {s for s in requested if s not in MCP_SCOPES} | set(MCP_SCOPES)
    return sorted(scopes & set(allowed))


class CISOAuthorizationForm(AuthorizationForm):
    """For MCP requests the user ticks what the app may do instead of scopes:
    read always, plus any of create, update and delete once the organization
    allows writes. A skip-consent client posts nothing and gets read only."""

    def __init__(
        self, *args, mcp_request=False, client_scopes=(), writes=False, **kwargs
    ):
        self._requested = kwargs["requested_scopes"]
        self._client_scopes = client_scopes
        super().__init__(*args, **kwargs)
        self.mcp_request = mcp_request
        self.writes = writes
        if mcp_request:
            del self.fields["scopes"]
            if writes:
                for action in WRITE_ACTIONS:
                    self.fields[f"can_{action}"] = forms.BooleanField(required=False)

    def clean(self):
        data = super().clean()
        if self.mcp_request and not self.errors:
            chosen = [bool(data.get(f"can_{action}")) for action in WRITE_ACTIONS]
            profile = ConnectionProfile.matching(*chosen)
            if profile is None:
                raise forms.ValidationError(_("No profile is available."))
            data["profile"] = profile
            data["scopes"] = profile_scopes(self._requested, self._client_scopes)
        return data


KNOX_COOKIE = "token"


def _user_from_knox_cookie(request):
    raw = request.COOKIES.get(KNOX_COOKIE)
    if not raw:
        return None
    try:
        user, _ = KnoxTokenAuthentication().authenticate_credentials(raw.encode())
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


def _access_denied_url(info, error="access_denied") -> str | None:
    redirect_uri = info.get("redirect_uri")
    if not redirect_uri:
        return None
    parts = urlsplit(redirect_uri)
    query = parse_qsl(parts.query, keep_blank_values=True) + [("error", error)]
    if info.get("state"):
        query.append(("state", info["state"]))
    query.append(("iss", get_adapter().get_issuer()))
    return urlunsplit(parts._replace(query=urlencode(query)))


def _silent_without_consent(request, info, mcp_request) -> bool:
    # allauth answers prompt=none from the user's tokens for any client, so a
    # client the user never approved could get a code without asking
    if "none" not in (request.GET.get("prompt") or "").split():
        return False
    approvals = (
        AppGrant.objects.all()
        if mcp_request
        else ConnectedAppUse.objects.filter(authorized_at__isnull=False)
    )
    user, client_id = request.user, info.get("client_id")
    if not approvals.filter(user=user, client_id=client_id).exists():
        return True
    # once all its tokens have expired (OAUTH_REFRESH_TOKEN_IDLE_DAYS), the
    # connection has ended: its grant row stays, but the user approves it again
    return not (
        Token.objects.valid()
        .filter(
            user=user,
            client_id=client_id,
            type__in=(Token.Type.ACCESS_TOKEN, Token.Type.REFRESH_TOKEN),
        )
        .exists()
    )


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

    form_class = CISOAuthorizationForm

    def _is_mcp_request(self) -> bool:
        return is_mcp_request(self._scopes, self._request_info.get("resources"))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        client = Client.objects.filter(id=self._request_info.get("client_id")).first()
        kwargs["mcp_request"] = self._is_mcp_request()
        kwargs["client_scopes"] = client.get_scopes() if client else []
        kwargs["writes"] = mcp_writes_enabled()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["self_registered"] = is_self_registered(context["client"])
        form = context["form"]
        if form.mcp_request and form.writes:
            context["write_choices"] = [
                (form[f"can_{action}"], label)
                for action, label in (
                    ("create", _("Create data")),
                    ("update", _("Change data")),
                    ("delete", _("Delete data")),
                )
            ]
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            user = _user_from_knox_cookie(request)
            if user is not None:
                request.user = user
        # before allauth: prompt=none and skip-consent clients get a code without
        # ever showing the consent page
        if request.user.is_authenticated:
            pending = _pending_request(request)
            if pending is not None:
                refusal = self._refusal(request, *pending)
                if refusal is not None:
                    return refusal
        response = super().dispatch(request, *args, **kwargs)
        location = response.get("Location") if response.status_code == 302 else None
        # absolute Location = going back to the client (RFC 9207)
        if location and urlsplit(location).scheme:
            response["Location"] = _with_iss(location, get_adapter().get_issuer())
        return response

    def _refusal(self, request, scopes, info):
        mcp_request = is_mcp_request(scopes, info.get("resources"))
        reason = refusal_reason(request.user, mcp_request)
        if reason is None:
            if _silent_without_consent(request, info, mcp_request):
                return HttpResponseRedirect(
                    _access_denied_url(info, error="consent_required")
                )
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
            user_id, client_id = self.request.user.pk, self._request_info["client_id"]
            ConnectedAppUse.record_authorization(user_id, client_id)
            if form.mcp_request:
                AppGrant.consent(user_id, client_id, form.cleaned_data["profile"])
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


def authorization_server_metadata(request):
    """RFC 8414 puts the metadata of the issuer <url>/api at
    /.well-known/oauth-authorization-server/api, outside /api. Some clients
    (Copilot Studio) try no other address."""
    response = oidc_configuration(request)
    response["Access-Control-Allow-Origin"] = "*"
    return response
