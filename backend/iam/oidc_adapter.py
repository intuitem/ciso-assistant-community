from urllib.parse import urlsplit, urlunsplit

from allauth.idp.oidc.adapter import DefaultOIDCAdapter
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# One scope to use MCP at all; what the app may do comes from its profile.
MCP_SCOPES = ["mcp"]
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
DEFAULT_PORTS = {"http": 80, "https": 443}


def canonical_url(url: str) -> str:
    """The URL as clients write it: lowercase host, no default port. Clients
    send https://host/mcp even when the instance is set to https://host:443."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = parts.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    port = parts.port
    netloc = host if port in (None, DEFAULT_PORTS.get(scheme)) else f"{host}:{port}"
    return urlunsplit((scheme, netloc, parts.path.rstrip("/"), parts.query, ""))


def public_url() -> str:
    return canonical_url(settings.CISO_ASSISTANT_URL)


def mcp_resource() -> str:
    return public_url() + "/mcp"


def is_mcp_resource(uri: str) -> bool:
    # refused, not normalised away: a resource has no user and no fragment
    try:
        parts = urlsplit(uri.strip())
        if parts.username is not None or parts.fragment or "\\" in uri:
            return False
        return canonical_url(uri) == mcp_resource()
    except ValueError:
        return False


class CISOOIDCAdapter(DefaultOIDCAdapter):
    scope_display = {
        **DefaultOIDCAdapter.scope_display,
        "mcp": _("Use CISO Assistant through MCP"),
    }

    def get_issuer(self) -> str:
        # allauth serves its metadata under /api/.well-known/, so the issuer must
        # carry /api for standard discovery to find it; and it must not follow the
        # Host header.
        return public_url() + "/api"

    def populate_server_metadata(self, data) -> None:
        data["authorization_response_iss_parameter_supported"] = True
        data["scopes_supported"] = [*data["scopes_supported"], *MCP_SCOPES]

    def validate_resource_uris(self, *, uris, **kwargs) -> None:
        for uri in uris:
            if not is_mcp_resource(uri):
                raise ValidationError(f"Unknown resource: {uri}")

    def validate_client_registration(self, *, client, **kwargs) -> None:
        from iam.mcp_access import mcp_enabled

        if not mcp_enabled():
            raise ValidationError("MCP is disabled on this instance.")
        # allauth's DCR form only checks that redirect_uris is a list of strings.
        allowed_hosts = settings.OAUTH_DCR_ALLOWED_REDIRECT_HOSTS
        for uri in client.get_redirect_uris():
            if "\\" in uri:
                raise ValidationError(f"Invalid redirect URI: {uri}")
            try:
                parts = urlsplit(uri)
                host = (parts.hostname or "").lower()
            except ValueError:
                raise ValidationError(f"Invalid redirect URI: {uri}")
            if not host:
                raise ValidationError(f"Redirect URI has no host: {uri}")
            is_loopback = parts.scheme == "http" and host in LOOPBACK_HOSTS
            if parts.scheme != "https" and not is_loopback:
                raise ValidationError(f"Redirect URI must use https: {uri}")
            if allowed_hosts and host not in allowed_hosts:
                raise ValidationError(f"Redirect host is not allowed: {host}")
        # Ignore what the client declares: these are the scopes a user may grant it.
        client.set_scopes(["openid", *MCP_SCOPES])
