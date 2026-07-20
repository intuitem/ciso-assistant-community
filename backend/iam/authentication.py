"""DRF authentication for OAuth2 service accounts.

Service accounts authenticate with the client_credentials grant against the
allauth OIDC IdP token endpoint. The resulting access tokens carry no user
(client_credentials has no resource owner), so this class maps the token's
client to its ServiceAccount and authenticates the request as the service
account's dedicated user, letting the regular RBAC machinery apply.
"""

from allauth.idp.oidc.contrib.rest_framework.authentication import (
    TokenAuthentication as OIDCTokenAuthentication,
)
from rest_framework import exceptions


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
