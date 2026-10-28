import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings


def _import_ca_mcp():
    # The image copies ca_mcp next to the backend code; a source checkout keeps
    # it in ../cli.
    try:
        import ca_mcp  # noqa: F401
    except ImportError:
        sys.path.insert(0, str(Path(settings.BASE_DIR).parent / "cli"))


def build_app():
    """The backend-mcp ASGI app. Django must already be set up."""
    from iam.oidc_adapter import CISOOIDCAdapter, mcp_resource

    public = urlsplit(settings.CISO_ASSISTANT_URL)
    # ca_mcp reads its configuration from the environment at import time.
    os.environ.setdefault("CA_MCP_TRANSPORT", "streamable-http")
    os.environ.setdefault("CA_MCP_ALLOWED_HOSTS", public.netloc)
    # only its path is used, to strip the prefix from pagination links
    os.environ.setdefault("API_URL", settings.CISO_ASSISTANT_URL.rstrip("/") + "/api")

    _import_ca_mcp()
    from ca_mcp import client
    from ca_mcp.server import build_oauth_http_app

    from mcp_server.oauth import CISOTokenVerifier
    from mcp_server.transport import dispatch

    client.set_transport(dispatch)
    issuer = CISOOIDCAdapter().get_issuer()
    app = build_oauth_http_app(
        token_verifier=CISOTokenVerifier(),
        issuer_url=issuer,
        resource_url=mcp_resource(),
    )
    return _with_authorization_server_metadata(app, urlsplit(issuer).path)


def _with_authorization_server_metadata(app, issuer_path):
    """Serve the RFC 8414 address of allauth's metadata.

    The issuer carries /api, so RFC 8414 puts its metadata at
    /.well-known/oauth-authorization-server/api: outside /api, where the proxy
    sends only us. Some clients (Copilot Studio) try no other address.
    """
    from asgiref.sync import sync_to_async
    from starlette.responses import Response

    from mcp_server.transport import anonymous_get

    path = "/.well-known/oauth-authorization-server" + issuer_path

    async def asgi(scope, receive, send):
        if scope["type"] == "http" and scope["path"] == path:
            upstream = await sync_to_async(anonymous_get)(
                "/.well-known/openid-configuration"
            )
            response = Response(
                upstream.content,
                status_code=upstream.status_code,
                media_type="application/json",
                headers={"Access-Control-Allow-Origin": "*"},
            )
            await response(scope, receive, send)
            return
        await app(scope, receive, send)

    return asgi
