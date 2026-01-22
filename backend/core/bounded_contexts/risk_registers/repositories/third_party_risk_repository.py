"""
Repository for ThirdPartyRisk aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.third_party_risk import ThirdPartyRisk


class ThirdPartyRiskRepository(Repository[ThirdPartyRisk]):
    """Repository for ThirdPartyRisk aggregates"""
    
    def __init__(self):
        super().__init__(ThirdPartyRisk)
    
    def find_by_title(self, title: str) -> Optional[ThirdPartyRisk]:
        """Find third party risk by title"""
        return ThirdPartyRisk.objects.filter(title=title).first()
    
    def find_by_third_party(self, third_party_id: UUID) -> List[ThirdPartyRisk]:
        """Find all risks for a specific third party"""
        return list(ThirdPartyRisk.objects.filter(thirdPartyIds__contains=[third_party_id]))
    
    def find_by_state(self, state: str) -> List[ThirdPartyRisk]:
        """Find all risks by lifecycle state"""
        return list(ThirdPartyRisk.objects.filter(lifecycle_state=state))

