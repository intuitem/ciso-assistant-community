"""
Repository for Requirement aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.requirement import Requirement


class RequirementRepository(Repository[Requirement]):
    """Repository for Requirement aggregates"""
    
    def __init__(self):
        super().__init__(Requirement)
    
    def find_by_code(self, framework_id: UUID, code: str) -> Optional[Requirement]:
        """Find requirement by framework and code"""
        return Requirement.objects.filter(frameworkId=framework_id, code=code).first()
    
    def find_by_framework(self, framework_id: UUID) -> List[Requirement]:
        """Find all requirements for a framework"""
        return list(Requirement.objects.filter(frameworkId=framework_id))
    
    def find_active(self) -> List[Requirement]:
        """Find all active requirements"""
        return list(
            Requirement.objects.filter(lifecycle_state=Requirement.LifecycleState.ACTIVE)
        )

