from allauth.idp.oidc.models import Token
from asgiref.sync import sync_to_async
from django.db import close_old_connections
from knox.auth import TokenAuthentication
from mcp.server.auth.provider import AccessToken
from rest_framework.exceptions import AuthenticationFailed

from iam.models import ConnectedAppUse
from iam.oidc_adapter import MCP_SCOPES, mcp_resource

PAT_CLIENT_ID = "personal-access-token"


def _from_oauth(raw: str, token: Token) -> AccessToken | None:
    user = token.user
    # client_credentials tokens carry no user: service accounts are not wired to MCP
    if user is None or not user.is_active:
        return None
    resources = token.get_resources()
    scopes = token.get_scopes()
    if resources:
        # RFC 8707: a token bound to another resource is not for us
        if mcp_resource() not in resources:
            return None
    elif not set(MCP_SCOPES) & set(scopes):
        return None
    ConnectedAppUse.record(user.pk, token.client_id)
    return AccessToken(
        token=raw,
        client_id=token.client_id,
        scopes=scopes,
        expires_at=int(token.expires_at.timestamp()) if token.expires_at else None,
        resource=mcp_resource(),
        subject=str(user.pk),
    )


def _from_personal_access_token(raw: str) -> AccessToken | None:
    # Keeps existing PAT setups ("API key" in Copilot Studio) working as Bearer.
    try:
        user, auth_token = TokenAuthentication().authenticate_credentials(raw.encode())
    except AuthenticationFailed:
        return None
    if not user.is_active:
        return None
    return AccessToken(
        token=raw,
        client_id=PAT_CLIENT_ID,
        scopes=list(MCP_SCOPES),
        expires_at=int(auth_token.expiry.timestamp()) if auth_token.expiry else None,
        resource=mcp_resource(),
        subject=str(user.pk),
    )


def verify(raw: str) -> AccessToken | None:
    token = (
        Token.objects.select_related("user")
        .valid()
        .by_value(raw)
        .filter(type=Token.Type.ACCESS_TOKEN)
        .first()
    )
    if token is not None:
        return _from_oauth(raw, token)
    return _from_personal_access_token(raw)


def _verify_in_thread(raw: str) -> AccessToken | None:
    # no request_started/finished signals outside Django's handler: recycle
    # stale connections by hand
    close_old_connections()
    try:
        return verify(raw)
    finally:
        close_old_connections()


class CISOTokenVerifier:
    async def verify_token(self, token: str) -> AccessToken | None:
        return await sync_to_async(_verify_in_thread)(token)
