"""
Repository for OrgUnit aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.org_unit import OrgUnit


class OrgUnitRepository(Repository[OrgUnit]):
    """Repository for OrgUnit aggregates"""
    
    def __init__(self):
        super().__init__(OrgUnit)
    
    def find_by_name(self, name: str) -> Optional[OrgUnit]:
        """Find organizational unit by name"""
        return OrgUnit.objects.filter(name=name).first()
    
    def find_by_ref_id(self, ref_id: str) -> Optional[OrgUnit]:
        """Find organizational unit by reference ID"""
        return OrgUnit.objects.filter(ref_id=ref_id).first()
    
    def find_children(self, parent_id: UUID) -> List[OrgUnit]:
        """Find all children of a parent organizational unit"""
        return list(OrgUnit.objects.filter(parentOrgUnitId=parent_id))
    
    def find_active(self) -> List[OrgUnit]:
        """Find all active organizational units"""
        return list(
            OrgUnit.objects.filter(lifecycle_state=OrgUnit.LifecycleState.ACTIVE)
        )

    # Alias for backward compatibility
    find_by_parent = find_children

