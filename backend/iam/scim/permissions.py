from rest_framework import permissions


class IsSCIMToken(permissions.BasePermission):
    """
    Passes if and only if the Knox token used for authentication was
    created as a SCIMToken (not a PersonalAccessToken or session token).
    """

    def has_permission(self, request, view):
        auth = request.auth  # Knox AuthToken instance, set by TokenAuthentication
        if auth is None:
            return False
        try:
            return auth.scim_token.exists()
        except Exception:
            return False
