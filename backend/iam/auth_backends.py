from asgiref.sync import sync_to_async
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import PermissionDenied


class LocalLoginBackend(ModelBackend):
    """Django's ModelBackend, refusing users who may not log in with a local
    password (see User.is_local). Checked at login, because forcing SSO does not
    make existing passwords unusable.

    It refuses with PermissionDenied, so Django tries no other backend: another
    one, such as allauth's, would accept the password.

    Only authenticate() checks it: SSO logins also record this backend in the
    session, and get_user() must keep returning their users."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(request, username, password, **kwargs)
        if user is not None and not user.is_local:
            raise PermissionDenied
        return user

    async def aauthenticate(self, request, **credentials):
        return await sync_to_async(self.authenticate)(request, **credentials)
