"""
Repository for ControlImplementation associations
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..associations.control_implementation import ControlImplementation


class ControlImplementationRepository(Repository[ControlImplementation]):
    """Repository for ControlImplementation associations"""

    def __init__(self):
        super().__init__(ControlImplementation)

    def find_by_control(self, control_id: UUID) -> List[ControlImplementation]:
        """Find all implementations for a control"""
        return list(ControlImplementation.objects.filter(controlId=control_id))

    def find_by_target(self, target_type: str, target_id: UUID) -> List[ControlImplementation]:
        """Find all implementations for a specific target"""
        return list(ControlImplementation.objects.filter(
            target_type=target_type,
            target_id=target_id
        ))

    def find_by_lifecycle_state(self, state: str) -> List[ControlImplementation]:
        """Find implementations by lifecycle state"""
        return list(ControlImplementation.objects.filter(lifecycle_state=state))

    def find_implemented(self) -> List[ControlImplementation]:
        """Find all implemented control implementations"""
        return list(ControlImplementation.objects.filter(
            lifecycle_state=ControlImplementation.LifecycleState.IMPLEMENTED
        ))

    def find_operating(self) -> List[ControlImplementation]:
        """Find all operating control implementations"""
        return list(ControlImplementation.objects.filter(
            lifecycle_state=ControlImplementation.LifecycleState.OPERATING
        ))

    def find_ineffective(self) -> List[ControlImplementation]:
        """Find all ineffective control implementations"""
        return list(ControlImplementation.objects.filter(
            lifecycle_state=ControlImplementation.LifecycleState.INEFFECTIVE
        ))

    def find_by_evidence(self, evidence_id: UUID) -> List[ControlImplementation]:
        """Find all implementations with a specific evidence item"""
        return list(ControlImplementation.objects.filter(evidenceIds__contains=[evidence_id]))

    def count_by_control(self, control_id: UUID) -> int:
        """Count implementations for a control"""
        return ControlImplementation.objects.filter(controlId=control_id).count()
