"""
Repository for AssetRisk aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.asset_risk import AssetRisk


class AssetRiskRepository(Repository[AssetRisk]):
    """Repository for AssetRisk aggregates"""
    
    def __init__(self):
        super().__init__(AssetRisk)
    
    def find_by_title(self, title: str) -> Optional[AssetRisk]:
        """Find asset risk by title"""
        return AssetRisk.objects.filter(title=title).first()
    
    def find_by_asset(self, asset_id: UUID) -> List[AssetRisk]:
        """Find all risks for a specific asset"""
        return list(AssetRisk.objects.filter(assetIds__contains=[asset_id]))
    
    def find_by_state(self, state: str) -> List[AssetRisk]:
        """Find all risks by lifecycle state"""
        return list(AssetRisk.objects.filter(lifecycle_state=state))
    
    def find_open_risks(self) -> List[AssetRisk]:
        """Find all open risks (not closed)"""
        return list(
            AssetRisk.objects.exclude(lifecycle_state=AssetRisk.LifecycleState.CLOSED)
        )

