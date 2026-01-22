"""
OrgUnit Projection Handlers

Update read models based on OrgUnit domain events.
"""

import uuid
from core.domain.events import EventHandler, DomainEvent
from ..read_models.org_unit_overview import OrgUnitOverview
from ..aggregates.org_unit import OrgUnit
from ..aggregates.user import User


class OrgUnitProjectionHandler(EventHandler):
    """
    Handler that updates OrgUnitOverview read model from domain events.
    """
    
    def handle(self, event: DomainEvent):
        """Handle domain events and update read model"""
        event_type = event.event_type
        
        if event_type == "OrgUnitCreated":
            self._create_overview(event)
        elif event_type == "OrgUnitActivated":
            self._update_overview(event)
        elif event_type == "OrgUnitRetired":
            self._update_overview(event)
        elif event_type == "ChildOrgUnitAdded":
            self._update_child_count(event)
        elif event_type == "OwnerAssignedToOrgUnit":
            self._update_owner_count(event)
    
    def _create_overview(self, event: DomainEvent):
        """Create overview when org unit is created"""
        org_unit_id = event.aggregate_id
        payload = event.payload
        
        try:
            org_unit = OrgUnit.objects.get(id=org_unit_id)
            OrgUnitOverview.objects.update_or_create(
                org_unit_id=org_unit_id,
                defaults={
                    "name": org_unit.name,
                    "ref_id": org_unit.ref_id,
                    "lifecycle_state": org_unit.lifecycle_state,
                    "child_count": len(org_unit.childOrgUnitIds),
                    "owner_count": len(org_unit.ownerUserIds),
                    "user_count": User.objects.filter(orgUnitIds__contains=[org_unit_id]).count(),
                }
            )
        except OrgUnit.DoesNotExist:
            pass  # Org unit not found, skip
    
    def _update_overview(self, event: DomainEvent):
        """Update overview when org unit state changes"""
        org_unit_id = event.aggregate_id
        
        try:
            org_unit = OrgUnit.objects.get(id=org_unit_id)
            OrgUnitOverview.objects.update_or_create(
                org_unit_id=org_unit_id,
                defaults={
                    "name": org_unit.name,
                    "ref_id": org_unit.ref_id,
                    "lifecycle_state": org_unit.lifecycle_state,
                    "child_count": len(org_unit.childOrgUnitIds),
                    "owner_count": len(org_unit.ownerUserIds),
                    "user_count": User.objects.filter(orgUnitIds__contains=[org_unit_id]).count(),
                }
            )
        except OrgUnit.DoesNotExist:
            pass
    
    def _update_child_count(self, event: DomainEvent):
        """Update child count when child is added"""
        parent_id = uuid.UUID(event.payload.get("parent_id"))
        
        try:
            parent = OrgUnit.objects.get(id=parent_id)
            OrgUnitOverview.objects.filter(org_unit_id=parent_id).update(
                child_count=len(parent.childOrgUnitIds)
            )
        except OrgUnit.DoesNotExist:
            pass
    
    def _update_owner_count(self, event: DomainEvent):
        """Update owner count when owner is assigned"""
        org_unit_id = uuid.UUID(event.payload.get("org_unit_id"))
        
        try:
            org_unit = OrgUnit.objects.get(id=org_unit_id)
            OrgUnitOverview.objects.filter(org_unit_id=org_unit_id).update(
                owner_count=len(org_unit.ownerUserIds)
            )
        except OrgUnit.DoesNotExist:
            pass

