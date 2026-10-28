from allauth.idp.oidc.contrib.rest_framework.authentication import (
    TokenAuthentication as OIDCTokenAuthentication,
)
from rest_framework import exceptions


def is_self_registered(client) -> bool:
    data = getattr(client, "data", None) or {}
    return bool(data.get("dcr") or data.get("cimd"))


class OIDCServiceAccountAuthentication(OIDCTokenAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            # No/invalid bearer token: fall through to the next authenticator.
            return None
        user, token = result
        client = getattr(token, "client", None)
        if user is not None and getattr(user, "is_authenticated", False):
            # Nobody vetted a self-registered client: the user only consented to
            # MCP scopes, and /api checks no scopes, so keep it off /api entirely.
            if client is not None and is_self_registered(client):
                raise exceptions.AuthenticationFailed(
                    "This client can only access the MCP endpoint."
                )
            if client is not None:
                from iam.models import ConnectedAppUse

                ConnectedAppUse.record(user.pk, client.pk)
            # User-bound OIDC token (e.g. authorization_code): honor as-is.
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
