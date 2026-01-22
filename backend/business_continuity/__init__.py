"""
DEPRECATED: Legacy Business Continuity Module

This module is DEPRECATED and should not be used.
Use core.bounded_contexts.business_continuity instead.

This legacy module is not registered as a Django app and has no active imports.
It is retained only for migration history reference.

For all new code, import from:
    from core.bounded_contexts.business_continuity import BusinessContinuityPlan, BcpTask, BcpAudit
"""

import warnings

warnings.warn(
    "The top-level 'business_continuity' module is deprecated. "
    "Use 'core.bounded_contexts.business_continuity' instead.",
    DeprecationWarning,
    stacklevel=2
)

__deprecated__ = True
__replacement__ = "core.bounded_contexts.business_continuity"
