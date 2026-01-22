"""
Repository for ThirdParty aggregates
"""

from typing import Optional, List
from core.domain.repository import Repository
from ..aggregates.third_party import ThirdParty


class ThirdPartyRepository(Repository[ThirdParty]):
    """Repository for ThirdParty aggregates"""
    
    def __init__(self):
        super().__init__(ThirdParty)
    
    def find_by_name(self, name: str) -> Optional[ThirdParty]:
        """Find third party by name"""
        return ThirdParty.objects.filter(name=name).first()
    
    def find_active(self) -> List[ThirdParty]:
        """Find all active third parties"""
        return list(
            ThirdParty.objects.filter(lifecycle_state=ThirdParty.LifecycleState.ACTIVE)
        )
    
    def find_by_criticality(self, criticality: str) -> List[ThirdParty]:
        """Find third parties by criticality"""
        return list(ThirdParty.objects.filter(criticality=criticality))
    
    def find_critical(self) -> List[ThirdParty]:
        """Find all critical third parties"""
        return list(
            ThirdParty.objects.filter(criticality=ThirdParty.Criticality.CRITICAL)
        )

