import os
from datetime import datetime

import structlog
from rest_framework import permissions

logger = structlog.get_logger(__name__)


class LicensePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        expiration_date_str = os.environ.get("LICENSE_EXPIRATION")

        if not expiration_date_str:
            # Handle the case where no expiration date is set
            logger.warning("License expiration date is not set.")
            return True

        try:
            expiration_date = datetime.fromisoformat(expiration_date_str)
        except ValueError:
            logger.error(
                "Invalid expiration date format. Expiration date should follow ISO 8601 format.",
                expiration_date=expiration_date_str,
            )
            return False

        if expiration_date < datetime.now():
            # License has expired, only allow read operations
            if request.method not in permissions.SAFE_METHODS:
                logger.warning(
                    "License has expired, only read operations are allowed.",
                    expiration_date=expiration_date,
                )
                return False

        # License is valid, allow all operations
        return True
