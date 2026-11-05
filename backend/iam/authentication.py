from allauth.idp.oidc.contrib.rest_framework.authentication import (
    TokenAuthentication as OIDCTokenAuthentication,
)
from knox.auth import TokenAuthentication
from rest_framework import exceptions


class KnoxTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, token):
        user, auth_token = super().authenticate_credentials(token)
        if auth_token.scim_token.exists():
            raise exceptions.AuthenticationFailed("Invalid token.")
        return user, auth_token


class OIDCServiceAccountAuthentication(OIDCTokenAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            # No/invalid bearer token: fall through to the next authenticator.
            return None
        user, token = result
        if user is not None and getattr(user, "is_authenticated", False):
            # User-bound OIDC token (e.g. authorization_code): honor as-is.
            return (user, token)
        client = getattr(token, "client", None)
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
