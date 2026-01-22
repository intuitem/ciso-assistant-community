"""
Repository for Service aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.service import Service


class ServiceRepository(Repository[Service]):
    """Repository for Service aggregates"""
    
    def __init__(self):
        super().__init__(Service)
    
    def find_by_name(self, name: str) -> Optional[Service]:
        """Find service by name"""
        return Service.objects.filter(name=name).first()
    
    def find_by_ref_id(self, ref_id: str) -> Optional[Service]:
        """Find service by reference ID"""
        return Service.objects.filter(ref_id=ref_id).first()
    
    def find_operational(self) -> List[Service]:
        """Find all operational services"""
        return list(
            Service.objects.filter(lifecycle_state=Service.LifecycleState.OPERATIONAL)
        )
    
    def find_by_asset(self, asset_id: UUID) -> List[Service]:
        """Find all services linked to a specific asset"""
        return list(Service.objects.filter(assetIds__contains=[asset_id]))
    
    def find_by_third_party(self, third_party_id: UUID) -> List[Service]:
        """Find all services linked to a specific third party"""
        return list(Service.objects.filter(thirdPartyIds__contains=[third_party_id]))

