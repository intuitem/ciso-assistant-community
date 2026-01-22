"""
DEPRECATED: Legacy Risk Registers Module

This module is DEPRECATED and should not be used.
Use core.bounded_contexts.risk_registers instead.

This legacy module is not registered as a Django app and has no active imports.
It is retained only for migration history reference.

For all new code, import from:
    from core.bounded_contexts.risk_registers.aggregates import AssetRisk, BusinessRisk, ThirdPartyRisk
    from core.bounded_contexts.risk_registers.repositories import AssetRiskRepository
"""

import warnings

warnings.warn(
    "The top-level 'risk_registers' module is deprecated. "
    "Use 'core.bounded_contexts.risk_registers' instead.",
    DeprecationWarning,
    stacklevel=2
)

__deprecated__ = True
__replacement__ = "core.bounded_contexts.risk_registers"
