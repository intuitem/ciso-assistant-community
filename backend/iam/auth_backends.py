from django.contrib.auth.backends import ModelBackend


class LocalLoginBackend(ModelBackend):
    """Django's ModelBackend, refusing users who may not log in with a local
    password (see User.is_local). Checked at login, because forcing SSO does not
    make existing passwords unusable.

    Only authenticate() checks it: SSO logins also record this backend in the
    session, and get_user() must keep returning their users."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(request, username, password, **kwargs)
        if user is not None and not user.is_local:
            return None
        return user
