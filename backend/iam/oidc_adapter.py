from urllib.parse import urlsplit

from allauth.idp.oidc.adapter import DefaultOIDCAdapter
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

MCP_SCOPES = ["mcp:read", "mcp:write"]
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def mcp_resource() -> str:
    return settings.CISO_ASSISTANT_URL.rstrip("/") + "/mcp"


class CISOOIDCAdapter(DefaultOIDCAdapter):
    scope_display = {
        **DefaultOIDCAdapter.scope_display,
        "mcp:read": _("Read your CISO Assistant data"),
        "mcp:write": _("Create and change data in CISO Assistant"),
    }

    def get_issuer(self) -> str:
        # allauth serves its metadata under /api/.well-known/, so the issuer must
        # carry /api for standard discovery to find it; and it must not follow the
        # Host header.
        return settings.CISO_ASSISTANT_URL.rstrip("/") + "/api"

    def populate_server_metadata(self, data) -> None:
        data["authorization_response_iss_parameter_supported"] = True
        data["scopes_supported"] = [*data["scopes_supported"], *MCP_SCOPES]

    def validate_resource_uris(self, *, uris, **kwargs) -> None:
        for uri in uris:
            if uri != mcp_resource():
                raise ValidationError(f"Unknown resource: {uri}")

    def validate_client_registration(self, *, client, **kwargs) -> None:
        # allauth's DCR form only checks that redirect_uris is a list of strings.
        allowed_hosts = settings.OAUTH_DCR_ALLOWED_REDIRECT_HOSTS
        for uri in client.get_redirect_uris():
            parts = urlsplit(uri)
            host = (parts.hostname or "").lower()
            is_loopback = parts.scheme == "http" and host in LOOPBACK_HOSTS
            if parts.scheme != "https" and not is_loopback:
                raise ValidationError(f"Redirect URI must use https: {uri}")
            if allowed_hosts and host not in allowed_hosts:
                raise ValidationError(f"Redirect host is not allowed: {host}")
        # Ignore what the client declares: these are the scopes a user may grant it.
        client.set_scopes(["openid", *MCP_SCOPES])
