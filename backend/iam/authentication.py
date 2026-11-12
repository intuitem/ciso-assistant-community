from allauth.idp.oidc.contrib.rest_framework.authentication import (
    TokenAuthentication as OIDCTokenAuthentication,
)
from knox.auth import TokenAuthentication
from rest_framework import exceptions


def is_self_registered(client) -> bool:
    data = getattr(client, "data", None) or {}
    return bool(data.get("dcr") or data.get("cimd"))


class KnoxTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, token):
        user, auth_token = super().authenticate_credentials(token)
        if auth_token.scim_token.exists():
            raise exceptions.AuthenticationFailed("Invalid token.")
        return user, auth_token


class OIDCServiceAccountAuthentication(OIDCTokenAuthentication):
    def authenticate(self, request):
        from core.context import mcp_access_var
        from iam.mcp_access import is_mcp_token

        # MCPTokenMiddleware checked the MCP token of this request
        access = mcp_access_var.get()
        if access is not None:
            return (access.user, access.token)
        result = super().authenticate(request)
        if result is None:
            # No/invalid bearer token: fall through to the next authenticator.
            return None
        user, token = result
        client = getattr(token, "client", None)
        if is_mcp_token(token):
            raise exceptions.AuthenticationFailed(
                "This AI app connection is not allowed."
            )
        if user is not None and getattr(user, "is_authenticated", False):
            # Nobody vetted a self-registered client: it gets nothing but MCP.
            if client is not None and is_self_registered(client):
                raise exceptions.AuthenticationFailed(
                    "This client can only access the MCP endpoint."
                )
            if client is not None:
                from iam.models import ConnectedAppUse

                ConnectedAppUse.record(user.pk, client.pk)
            return (user, token)
        service_account = (
            getattr(client, "service_account", None) if client is not None else None
        )
        if service_account is None:
            raise exceptions.AuthenticationFailed(
                "Token is not bound to a service account."
            )
        if not service_account.is_active or not service_account.user.is_active:
            raise exceptions.AuthenticationFailed("Service account is inactive.")
        return (service_account.user, token)
