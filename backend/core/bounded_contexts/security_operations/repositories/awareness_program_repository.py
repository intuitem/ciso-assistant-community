"""
Repository for AwarenessProgram aggregates
"""

from typing import Optional, List
from core.domain.repository import Repository
from ..aggregates.awareness_program import AwarenessProgram


class AwarenessProgramRepository(Repository[AwarenessProgram]):
    """Repository for AwarenessProgram aggregates"""
    
    def __init__(self):
        super().__init__(AwarenessProgram)
    
    def find_by_name(self, name: str) -> Optional[AwarenessProgram]:
        """Find program by name"""
        return AwarenessProgram.objects.filter(name=name).first()
    
    def find_active(self) -> List[AwarenessProgram]:
        """Find all active programs"""
        return list(
            AwarenessProgram.objects.filter(lifecycle_state=AwarenessProgram.LifecycleState.ACTIVE)
        )

