"""
Middleware for validating client account status.
Blocks access if the user's account is expired or suspended.
"""

from django.http import JsonResponse
from django.utils import timezone
from rest_framework import status

import structlog

logger = structlog.get_logger(__name__)


class AccountValidationMiddleware:
    """
    Middleware to validate that the user's account is active and not expired.
    Superusers are exempt from this check.
    """

    # Paths that don't require account validation (login, logout, etc.)
    EXEMPT_PATHS = [
        "/api/iam/login/",
        "/api/iam/logout/",
        "/api/csrf/",
        "/api/iam/password-reset/",
        "/api/iam/password-reset-confirm/",
        "/api/schema/",
        "/api/schema/swagger/",
        "/api/schema/redoc/",
        "/api/health/",
        "/api/accounts/",  # Admin panel for managing accounts
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip validation for unauthenticated requests
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return self.get_response(request)

        # Superusers are exempt
        if request.user.is_superuser:
            return self.get_response(request)

        # Check if path is exempt
        path = request.path
        for exempt_path in self.EXEMPT_PATHS:
            if path.startswith(exempt_path):
                return self.get_response(request)

        # Get the user's account
        account = self._get_user_account(request.user)

        if account:
            # Check account status
            if account.status == "suspended":
                logger.warning(
                    "Access blocked - account suspended",
                    user=request.user.email,
                    account=account.name,
                )
                return JsonResponse(
                    {
                        "error": "account_suspended",
                        "message": "Your account has been suspended. Please contact support.",
                        "account_name": account.name,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if account.status == "expired" or account.is_expired:
                logger.warning(
                    "Access blocked - account expired",
                    user=request.user.email,
                    account=account.name,
                    expiry_date=str(account.subscription_end),
                )
                return JsonResponse(
                    {
                        "error": "account_expired",
                        "message": "Your subscription has expired. Please renew to continue.",
                        "account_name": account.name,
                        "expiry_date": str(account.subscription_end),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        return self.get_response(request)

    def _get_user_account(self, user):
        """
        Get the ClientAccount associated with the user.
        A user belongs to an account through their UserGroup -> Folder -> ClientAccount relationship.
        """
        from accounts.models import ClientAccount
        from iam.models import UserGroup

        # Get user's groups and find associated accounts
        user_groups = user.user_groups.all()
        for group in user_groups:
            if group.folder:
                try:
                    return ClientAccount.objects.get(folder=group.folder)
                except ClientAccount.DoesNotExist:
                    # Try parent folder
                    parent = group.folder.parent_folder
                    if parent:
                        try:
                            return ClientAccount.objects.get(folder=parent)
                        except ClientAccount.DoesNotExist:
                            pass

        return None


def get_user_account(user):
    """
    Utility function to get the ClientAccount for a user.
    Can be used outside of middleware context.
    """
    from accounts.models import ClientAccount
    from iam.models import UserGroup

    if not user or not user.is_authenticated:
        return None

    # Superusers don't have accounts
    if user.is_superuser:
        return None

    user_groups = user.user_groups.all()
    for group in user_groups:
        if group.folder:
            try:
                return ClientAccount.objects.get(folder=group.folder)
            except ClientAccount.DoesNotExist:
                parent = group.folder.parent_folder
                if parent:
                    try:
                        return ClientAccount.objects.get(folder=parent)
                    except ClientAccount.DoesNotExist:
                        pass

    return None
