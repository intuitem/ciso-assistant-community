"""
Repository for Asset aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.asset import Asset


class AssetRepository(Repository[Asset]):
    """Repository for Asset aggregates"""
    
    def __init__(self):
        super().__init__(Asset)
    
    def find_by_name(self, name: str) -> Optional[Asset]:
        """Find asset by name"""
        return Asset.objects.filter(name=name).first()
    
    def find_by_ref_id(self, ref_id: str) -> Optional[Asset]:
        """Find asset by reference ID"""
        return Asset.objects.filter(ref_id=ref_id).first()
    
    def find_by_type(self, asset_type: str) -> List[Asset]:
        """Find assets by type"""
        return list(Asset.objects.filter(asset_type=asset_type))
    
    def find_active(self) -> List[Asset]:
        """Find all active (InUse) assets"""
        return list(
            Asset.objects.filter(lifecycle_state=Asset.LifecycleState.IN_USE)
        )
    
    def find_by_control(self, control_id: UUID) -> List[Asset]:
        """Find all assets with a specific control"""
        return list(Asset.objects.filter(controlIds__contains=[control_id]))
    
    def find_by_risk(self, risk_id: UUID) -> List[Asset]:
        """Find all assets with a specific risk"""
        return list(Asset.objects.filter(riskIds__contains=[risk_id]))
    
    def find_by_service(self, service_id: UUID) -> List[Asset]:
        """Find all assets linked to a specific service"""
        return list(Asset.objects.filter(serviceIds__contains=[service_id]))

