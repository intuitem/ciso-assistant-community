"""
Repository for Process aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.process import Process


class ProcessRepository(Repository[Process]):
    """Repository for Process aggregates"""
    
    def __init__(self):
        super().__init__(Process)
    
    def find_by_name(self, name: str) -> Optional[Process]:
        """Find process by name"""
        return Process.objects.filter(name=name).first()
    
    def find_by_ref_id(self, ref_id: str) -> Optional[Process]:
        """Find process by reference ID"""
        return Process.objects.filter(ref_id=ref_id).first()
    
    def find_active(self) -> List[Process]:
        """Find all active processes"""
        return list(
            Process.objects.filter(lifecycle_state=Process.LifecycleState.ACTIVE)
        )
    
    def find_by_org_unit(self, org_unit_id: UUID) -> List[Process]:
        """Find all processes assigned to a specific organizational unit"""
        return list(Process.objects.filter(orgUnitIds__contains=[org_unit_id]))
    
    def find_by_asset(self, asset_id: UUID) -> List[Process]:
        """Find all processes linked to a specific asset"""
        return list(Process.objects.filter(assetIds__contains=[asset_id]))

