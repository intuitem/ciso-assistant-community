"""
Risk Registers Repositories
"""

from .asset_risk_repository import AssetRiskRepository
from .third_party_risk_repository import ThirdPartyRiskRepository
from .business_risk_repository import BusinessRiskRepository

__all__ = ["AssetRiskRepository", "ThirdPartyRiskRepository", "BusinessRiskRepository"]

