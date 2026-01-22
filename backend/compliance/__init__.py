"""
DEPRECATED: Legacy Compliance Module

This module is DEPRECATED and should not be used.
Use core.bounded_contexts.compliance instead.

This legacy module is not registered as a Django app and has no active imports.
It is retained only for migration history reference.

For all new code, import from:
    from core.bounded_contexts.compliance.aggregates import ComplianceFramework, ComplianceRequirement
    from core.bounded_contexts.compliance.repositories import ComplianceFrameworkRepository
"""

import warnings

warnings.warn(
    "The top-level 'compliance' module is deprecated. "
    "Use 'core.bounded_contexts.compliance' instead.",
    DeprecationWarning,
    stacklevel=2
)

__deprecated__ = True
__replacement__ = "core.bounded_contexts.compliance"
