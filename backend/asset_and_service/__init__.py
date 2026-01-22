"""
DEPRECATED: Legacy Asset and Service Module

This module is DEPRECATED and should not be used.
Use core.bounded_contexts.asset_and_service instead.

This legacy module is not registered as a Django app and has no active imports.
It is retained only for migration history reference.

For all new code, import from:
    from core.bounded_contexts.asset_and_service.aggregates import Asset, Service, Process
    from core.bounded_contexts.asset_and_service.repositories import AssetRepository
"""

import warnings

warnings.warn(
    "The top-level 'asset_and_service' module is deprecated. "
    "Use 'core.bounded_contexts.asset_and_service' instead.",
    DeprecationWarning,
    stacklevel=2
)

__deprecated__ = True
__replacement__ = "core.bounded_contexts.asset_and_service"
