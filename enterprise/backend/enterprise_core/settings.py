import os
import structlog
from ciso_assistant.settings import *

# -----------------------------------------------------------------------------
# Configuration Overrides
# -----------------------------------------------------------------------------

# Override default Log Level if not set in ENV (Community defaults to WARNING)
if "LOG_LEVEL" not in os.environ:
    LOG_LEVEL = "INFO"
    # Note: LOGGING dict was already configured in the base import.
    # To strictly enforce INFO without an ENV var, you would need to update
    # LOGGING['loggers']['']['level'] and re-run dictConfig here.
    # However, it is cleaner to manage this via the .env file.

# -----------------------------------------------------------------------------
# Enterprise Application Definition
# -----------------------------------------------------------------------------

logger = structlog.getLogger(__name__)

logger.info("Launching CISO Assistant Enterprise")

# 1. Extend Installed Apps
INSTALLED_APPS.append("enterprise_core")

# 2. Extend DRF Permissions
REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"].append(
    "enterprise_core.permissions.LicensePermission"
)

# 3. Define Enterprise Modules & Routes
# (The base file defined these as empty dicts, so we populate them now)
MODULE_PATHS["serializers"] = "enterprise_core.serializers"

ROUTES["client-settings"] = {
    "viewset": "enterprise_core.views.ClientSettingsViewSet",
    "basename": "client-settings",
}

MODULES["enterprise_core"] = {
    "path": "",
    "module": "enterprise_core.urls",
}

# -----------------------------------------------------------------------------
# Licensing
# -----------------------------------------------------------------------------

LICENSE_SEATS = int(os.environ.get("LICENSE_SEATS", 1))
LICENSE_EXPIRATION = os.environ.get("LICENSE_EXPIRATION", "unset")

logger.info("License information", seats=LICENSE_SEATS, expiration=LICENSE_EXPIRATION)

logger.info(
    "Enterprise startup information",
    feature_flags=FEATURE_FLAGS,
    module_paths=MODULE_PATHS,
)
