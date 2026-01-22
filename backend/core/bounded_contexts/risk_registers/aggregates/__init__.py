"""
Risk Registers Aggregates
"""

from .asset_risk import AssetRisk
from .third_party_risk import ThirdPartyRisk
from .business_risk import BusinessRisk

__all__ = ["AssetRisk", "ThirdPartyRisk", "BusinessRisk"]

