"""
Repository for ComplianceFramework aggregates
"""

from typing import Optional, List
from core.domain.repository import Repository
from ..aggregates.compliance_framework import ComplianceFramework


class ComplianceFrameworkRepository(Repository[ComplianceFramework]):
    """Repository for ComplianceFramework aggregates"""
    
    def __init__(self):
        super().__init__(ComplianceFramework)
    
    def find_by_name(self, name: str) -> Optional[ComplianceFramework]:
        """Find framework by name"""
        return ComplianceFramework.objects.filter(name=name).first()
    
    def find_active(self) -> List[ComplianceFramework]:
        """Find all active frameworks"""
        return list(
            ComplianceFramework.objects.filter(lifecycle_state=ComplianceFramework.LifecycleState.ACTIVE)
        )

