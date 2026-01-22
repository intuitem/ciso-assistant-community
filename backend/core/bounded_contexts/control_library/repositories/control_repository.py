"""
Repository for Control aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.control import Control


class ControlRepository(Repository[Control]):
    """Repository for Control aggregates"""
    
    def __init__(self):
        super().__init__(Control)
    
    def find_by_name(self, name: str) -> Optional[Control]:
        """Find control by name"""
        return Control.objects.filter(name=name).first()
    
    def find_by_ref_id(self, ref_id: str) -> Optional[Control]:
        """Find control by reference ID"""
        return Control.objects.filter(ref_id=ref_id).first()
    
    def find_approved(self) -> List[Control]:
        """Find all approved controls"""
        return list(
            Control.objects.filter(lifecycle_state=Control.LifecycleState.APPROVED)
        )
    
    def find_by_type(self, control_type: str) -> List[Control]:
        """Find controls by type"""
        return list(Control.objects.filter(control_type=control_type))
    
    def find_by_legal_requirement(self, requirement_id: UUID) -> List[Control]:
        """Find all controls with a specific legal requirement"""
        return list(Control.objects.filter(legalRequirementIds__contains=[requirement_id]))

