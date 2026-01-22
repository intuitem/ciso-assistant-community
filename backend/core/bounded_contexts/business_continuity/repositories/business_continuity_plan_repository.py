"""
Repository for BusinessContinuityPlan aggregates
"""

from typing import Optional, List
from core.domain.repository import Repository
from ..aggregates.business_continuity_plan import BusinessContinuityPlan


class BusinessContinuityPlanRepository(Repository[BusinessContinuityPlan]):
    """Repository for BusinessContinuityPlan aggregates"""
    
    def __init__(self):
        super().__init__(BusinessContinuityPlan)
    
    def find_by_name(self, name: str) -> Optional[BusinessContinuityPlan]:
        """Find BCP by name"""
        return BusinessContinuityPlan.objects.filter(name=name).first()
    
    def find_approved(self) -> List[BusinessContinuityPlan]:
        """Find all approved BCPs"""
        return list(
            BusinessContinuityPlan.objects.filter(
                lifecycle_state=BusinessContinuityPlan.LifecycleState.APPROVED
            )
        )
    
    def find_exercised(self) -> List[BusinessContinuityPlan]:
        """Find all exercised BCPs"""
        return list(
            BusinessContinuityPlan.objects.filter(
                lifecycle_state=BusinessContinuityPlan.LifecycleState.EXERCISED
            )
        )

