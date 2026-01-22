"""
Repository for DataAsset aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.data_asset import DataAsset


class DataAssetRepository(Repository[DataAsset]):
    """Repository for DataAsset aggregates"""
    
    def __init__(self):
        super().__init__(DataAsset)
    
    def find_by_name(self, name: str) -> Optional[DataAsset]:
        """Find data asset by name"""
        return DataAsset.objects.filter(name=name).first()
    
    def find_with_personal_data(self) -> List[DataAsset]:
        """Find all data assets containing personal data"""
        return list(DataAsset.objects.filter(contains_personal_data=True))
    
    def find_by_asset(self, asset_id: UUID) -> List[DataAsset]:
        """Find all data assets stored on a specific asset"""
        return list(DataAsset.objects.filter(assetIds__contains=[asset_id]))
    
    def find_active(self) -> List[DataAsset]:
        """Find all active data assets"""
        return list(
            DataAsset.objects.filter(lifecycle_state=DataAsset.LifecycleState.ACTIVE)
        )

