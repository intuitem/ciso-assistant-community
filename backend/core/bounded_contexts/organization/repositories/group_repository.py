"""
Repository for Group aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.group import Group


class GroupRepository(Repository[Group]):
    """Repository for Group aggregates"""
    
    def __init__(self):
        super().__init__(Group)
    
    def find_by_name(self, name: str) -> Optional[Group]:
        """Find group by name"""
        return Group.objects.filter(name=name).first()
    
    def find_by_user(self, user_id: UUID) -> List[Group]:
        """Find all groups a user belongs to"""
        return list(Group.objects.filter(userIds__contains=[user_id]))
    
    def find_active(self) -> List[Group]:
        """Find all active groups"""
        return list(
            Group.objects.filter(lifecycle_state=Group.LifecycleState.ACTIVE)
        )

