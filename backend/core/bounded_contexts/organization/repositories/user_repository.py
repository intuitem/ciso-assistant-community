"""
Repository for User aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.user import User


class UserRepository(Repository[User]):
    """Repository for User aggregates"""
    
    def __init__(self):
        super().__init__(User)
    
    def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email"""
        return User.objects.filter(email__iexact=email).first()
    
    def find_by_group(self, group_id: UUID) -> List[User]:
        """Find all users in a specific group"""
        return list(User.objects.filter(groupIds__contains=[group_id]))
    
    def find_by_org_unit(self, org_unit_id: UUID) -> List[User]:
        """Find all users in a specific organizational unit"""
        return list(User.objects.filter(orgUnitIds__contains=[org_unit_id]))
    
    def find_active(self) -> List[User]:
        """Find all active users"""
        return list(
            User.objects.filter(lifecycle_state=User.LifecycleState.ACTIVE)
        )

