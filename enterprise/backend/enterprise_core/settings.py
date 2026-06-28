"""
Enterprise settings — imports everything from the community settings and
applies EE-only overrides (license, extra routes, serializer path, etc.).
"""

import os
import structlog

from ciso_assistant.settings import *  # noqa: F403, F401

logger = structlog.getLogger(__name__)

# --- Library path fallback ---
# In EE the library directory may sit outside the usual relative path.
_lib_path = BASE_DIR / "library/libraries"  # noqa: F405
if not _lib_path.is_dir():
    _lib_path = BASE_DIR.parent.parent / "backend" / "library" / "libraries"  # noqa: F405
LIBRARIES_PATH = library_path = _lib_path

# --- EE module wiring ---
MODULE_PATHS["serializers"] = "enterprise_core.serializers"  # noqa: F405

REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"].append(  # noqa: F405
    "enterprise_core.permissions.LicensePermission"
)

ROUTES["client-settings"] = {  # noqa: F405
    "viewset": "enterprise_core.views.ClientSettingsViewSet",
    "basename": "client-settings",
}

ROUTES["custom-email-templates"] = {  # noqa: F405
    "viewset": "enterprise_core.views.CustomEmailTemplateViewSet",
    "basename": "custom-email-templates",
}

ROUTES["custom-word-templates"] = {  # noqa: F405
    "viewset": "enterprise_core.views.CustomWordTemplateViewSet",
    "basename": "custom-word-templates",
}

MODULES["enterprise_core"] = {  # noqa: F405
    "path": "",
    "module": "enterprise_core.urls",
}

INSTALLED_APPS.append("enterprise_core")  # noqa: F405

# --- License ---
LICENSE_SEATS = int(os.environ.get("LICENSE_SEATS", 1))
LICENSE_EXPIRATION = os.environ.get("LICENSE_EXPIRATION", "unset")

# --- Startup banner ---
logger.info("Launching CISO Assistant Enterprise")
logger.info(
    "Enterprise startup information",
    feature_flags=FEATURE_FLAGS,  # noqa: F405
    module_paths=MODULE_PATHS,  # noqa: F405
)
logger.info("License information", seats=LICENSE_SEATS, expiration=LICENSE_EXPIRATION)
