"""
DEPRECATED: Legacy Control Library Module

This module is DEPRECATED and should not be used.
Use core.bounded_contexts.control_library instead.

This legacy module is not registered as a Django app and has no active imports.
It is retained only for migration history reference.

For all new code, import from:
    from core.bounded_contexts.control_library.aggregates import Control, Policy, EvidenceItem
    from core.bounded_contexts.control_library.repositories import ControlRepository
"""

import warnings

warnings.warn(
    "The top-level 'control_library' module is deprecated. "
    "Use 'core.bounded_contexts.control_library' instead.",
    DeprecationWarning,
    stacklevel=2
)

__deprecated__ = True
__replacement__ = "core.bounded_contexts.control_library"
