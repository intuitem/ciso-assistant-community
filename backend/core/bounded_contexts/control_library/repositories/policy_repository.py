"""
Repository for Policy aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.policy import Policy


class PolicyRepository(Repository[Policy]):
    """Repository for Policy aggregates"""
    
    def __init__(self):
        super().__init__(Policy)
    
    def find_by_title(self, title: str) -> Optional[Policy]:
        """Find policy by title"""
        return Policy.objects.filter(title=title).first()
    
    def find_published(self) -> List[Policy]:
        """Find all published policies"""
        return list(
            Policy.objects.filter(lifecycle_state=Policy.LifecycleState.PUBLISHED)
        )
    
    def find_by_owner(self, user_id: UUID) -> List[Policy]:
        """Find all policies owned by a user"""
        return list(Policy.objects.filter(ownerUserIds__contains=[user_id]))
    
    def find_by_org_unit(self, org_unit_id: UUID) -> List[Policy]:
        """Find all policies applicable to an organizational unit"""
        return list(Policy.objects.filter(applicableOrgUnitIds__contains=[org_unit_id]))

