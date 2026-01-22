"""
User Projection Handlers

Update read models based on User domain events.
"""

import uuid
from core.domain.events import EventHandler, DomainEvent
from ..read_models.user_overview import UserOverview
from ..aggregates.user import User
from ..aggregates.group import Group
from ..aggregates.org_unit import OrgUnit


class UserProjectionHandler(EventHandler):
    """
    Handler that updates UserOverview read model from domain events.
    """
    
    def handle(self, event: DomainEvent):
        """Handle domain events and update read model"""
        event_type = event.event_type
        
        if event_type == "UserCreated":
            self._create_overview(event)
        elif event_type == "UserActivated":
            self._update_overview(event)
        elif event_type == "UserDisabled":
            self._update_overview(event)
        elif event_type == "UserAssignedToGroup":
            self._update_group_info(event)
        elif event_type == "UserAssignedToOrgUnit":
            self._update_org_unit_info(event)
    
    def _create_overview(self, event: DomainEvent):
        """Create overview when user is created"""
        user_id = event.aggregate_id
        
        try:
            user = User.objects.get(id=user_id)
            self._update_overview_from_user(user)
        except User.DoesNotExist:
            pass
    
    def _update_overview(self, event: DomainEvent):
        """Update overview when user state changes"""
        user_id = event.aggregate_id
        
        try:
            user = User.objects.get(id=user_id)
            self._update_overview_from_user(user)
        except User.DoesNotExist:
            pass
    
    def _update_group_info(self, event: DomainEvent):
        """Update group information when user is assigned to group"""
        user_id = uuid.UUID(event.payload.get("user_id"))
        
        try:
            user = User.objects.get(id=user_id)
            self._update_overview_from_user(user)
        except User.DoesNotExist:
            pass
    
    def _update_org_unit_info(self, event: DomainEvent):
        """Update org unit information when user is assigned to org unit"""
        user_id = uuid.UUID(event.payload.get("user_id"))
        
        try:
            user = User.objects.get(id=user_id)
            self._update_overview_from_user(user)
        except User.DoesNotExist:
            pass
    
    def _update_overview_from_user(self, user: User):
        """Update overview from user aggregate"""
        # Get group names
        group_names = []
        if user.groupIds:
            groups = Group.objects.filter(id__in=user.groupIds)
            group_names = [g.name for g in groups]
        
        # Get org unit names
        org_unit_names = []
        if user.orgUnitIds:
            org_units = OrgUnit.objects.filter(id__in=user.orgUnitIds)
            org_unit_names = [ou.name for ou in org_units]
        
        # Update or create overview
        UserOverview.objects.update_or_create(
            user_id=user.id,
            defaults={
                "email": user.email,
                "display_name": user.display_name or user.full_name,
                "lifecycle_state": user.lifecycle_state,
                "group_count": len(user.groupIds),
                "org_unit_count": len(user.orgUnitIds),
                "group_names": group_names,
                "org_unit_names": org_unit_names,
                # Note: responsibility_count would need to query ResponsibilityAssignment
            }
        )

