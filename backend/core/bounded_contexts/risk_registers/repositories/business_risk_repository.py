"""
Repository for BusinessRisk aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.business_risk import BusinessRisk


class BusinessRiskRepository(Repository[BusinessRisk]):
    """Repository for BusinessRisk aggregates"""
    
    def __init__(self):
        super().__init__(BusinessRisk)
    
    def find_by_title(self, title: str) -> Optional[BusinessRisk]:
        """Find business risk by title"""
        return BusinessRisk.objects.filter(title=title).first()
    
    def find_by_process(self, process_id: UUID) -> List[BusinessRisk]:
        """Find all risks for a specific process"""
        return list(BusinessRisk.objects.filter(processIds__contains=[process_id]))
    
    def find_by_org_unit(self, org_unit_id: UUID) -> List[BusinessRisk]:
        """Find all risks for a specific organizational unit"""
        return list(BusinessRisk.objects.filter(orgUnitIds__contains=[org_unit_id]))
    
    def find_by_state(self, state: str) -> List[BusinessRisk]:
        """Find all risks by lifecycle state"""
        return list(BusinessRisk.objects.filter(lifecycle_state=state))

