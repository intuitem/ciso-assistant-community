"""Service account authentication."""

import jwt
import requests
from allauth.idp.oidc.contrib.rest_framework.authentication import (
    TokenAuthentication as OIDCTokenAuthentication,
)
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header

from iam.models import ServiceAccount
from iam.oidc_federation import (
    resolve_social_app_provider_config,
    verify_and_decode_cached,
)


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


class FederatedServiceAccountAuthentication(BaseAuthentication):
    keyword = "bearer"

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != self.keyword.encode():
            return None
        if len(auth) != 2:
            return None
        token = auth[1].decode()

        try:
            unverified = jwt.decode(token, options={"verify_signature": False})
        except jwt.PyJWTError:
            return None
        aud = unverified.get("aud")
        aud_candidates = aud if isinstance(aud, list) else [aud] if aud else []
        if not aud_candidates:
            return None

        service_account = (
            ServiceAccount.objects.filter(
                identity_source=ServiceAccount.IdentitySource.FEDERATED,
                social_app__client_id__in=aud_candidates,
            )
            .select_related("social_app", "user")
            .first()
        )
        if service_account is None:
            return None

        try:
            provider_config = resolve_social_app_provider_config(
                service_account.social_app
            )
            claims = verify_and_decode_cached(
                credential=token,
                keys_url=provider_config["jwks_uri"],
                issuer=provider_config["issuer"],
                audience=[service_account.social_app.client_id],
            )
        except (OAuth2Error, KeyError, requests.RequestException) as error:
            raise exceptions.AuthenticationFailed("Invalid token.") from error

        if claims.get("sub") != service_account.federated_subject:
            raise exceptions.AuthenticationFailed(
                "Token subject does not match the registered service account."
            )
        if not service_account.is_active or not service_account.user.is_active:
            raise exceptions.AuthenticationFailed("Service account is inactive.")

        return (service_account.user, token)

    def authenticate_header(self, request):
        return "Bearer"
