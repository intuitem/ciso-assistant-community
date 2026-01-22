"""
OrgUnit Aggregate

Represents an organizational unit in the organization hierarchy.
"""

import uuid
from typing import Optional, List
from django.db import models
from django.core.exceptions import ValidationError

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    OrgUnitCreated,
    OrgUnitActivated,
    OrgUnitRetired,
    ChildOrgUnitAdded,
    OwnerAssignedToOrgUnit,
)


class OrgUnit(AggregateRoot):
    """
    Organizational Unit aggregate root.
    
    Represents a unit in the organizational hierarchy (department, division, etc.).
    Uses embedded ID arrays for child units and owners.
    """
    
    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        RETIRED = "retired", "Retired"
    
    # Basic fields
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    ref_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.DRAFT,
        db_index=True
    )
    
    # Hierarchy (embedded ID arrays)
    parentOrgUnitId = models.UUIDField(null=True, blank=True, db_index=True)
    childOrgUnitIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of child organizational unit IDs"
    )
    
    # Ownership (embedded ID arrays)
    ownerUserIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of owner user IDs"
    )
    
    # Tags (for filtering/labeling)
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "organization_org_units"
        verbose_name = "Organizational Unit"
        verbose_name_plural = "Organizational Units"
        indexes = [
            models.Index(fields=["parentOrgUnitId", "lifecycle_state"]),
            models.Index(fields=["name"]),
        ]
    
    def clean(self):
        """Validate aggregate invariants"""
        super().clean()
        
        # Invariant: No cycles in parent/child graph
        if self.parentOrgUnitId:
            if self.parentOrgUnitId == self.id:
                raise ValidationError("OrgUnit cannot be its own parent")
            
            # Check for cycles (would need recursive check in real implementation)
            # For now, basic validation
    
    def create(self, name: str, description: str = None, ref_id: str = None, parent_id: Optional[uuid.UUID] = None):
        """
        Create a new organizational unit.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.description = description
        self.ref_id = ref_id
        self.parentOrgUnitId = parent_id
        self.lifecycle_state = self.LifecycleState.DRAFT
        
        # Raise domain event
        event = OrgUnitCreated()
        event.payload = {
            "name": name,
            "ref_id": ref_id,
            "parent_id": str(parent_id) if parent_id else None,
        }
        self._raise_event(event)
    
    def activate(self):
        """Activate the organizational unit"""
        if self.lifecycle_state != self.LifecycleState.ACTIVE:
            self.lifecycle_state = self.LifecycleState.ACTIVE
            
            event = OrgUnitActivated()
            event.payload = {
                "org_unit_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def retire(self):
        """Retire the organizational unit"""
        if self.lifecycle_state != self.LifecycleState.RETIRED:
            # Business rule: Cannot retire if it has active children
            if self.childOrgUnitIds:
                active_children = OrgUnit.objects.filter(
                    id__in=self.childOrgUnitIds,
                    lifecycle_state=self.LifecycleState.ACTIVE
                ).exists()
                if active_children:
                    raise ValidationError("Cannot retire OrgUnit with active children")
            
            self.lifecycle_state = self.LifecycleState.RETIRED
            
            event = OrgUnitRetired()
            event.payload = {
                "org_unit_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def add_child(self, child_id: uuid.UUID):
        """
        Add a child organizational unit.
        
        Args:
            child_id: UUID of the child organizational unit
        """
        if child_id not in self.childOrgUnitIds:
            self.childOrgUnitIds.append(child_id)
            
            event = ChildOrgUnitAdded()
            event.payload = {
                "parent_id": str(self.id),
                "child_id": str(child_id),
            }
            self._raise_event(event)
    
    def assign_owner(self, user_id: uuid.UUID):
        """
        Assign an owner to this organizational unit.
        
        Args:
            user_id: UUID of the user to assign as owner
        """
        if user_id not in self.ownerUserIds:
            self.ownerUserIds.append(user_id)
            
            event = OwnerAssignedToOrgUnit()
            event.payload = {
                "org_unit_id": str(self.id),
                "user_id": str(user_id),
            }
            self._raise_event(event)
    
    def remove_owner(self, user_id: uuid.UUID):
        """Remove an owner from this organizational unit"""
        if user_id in self.ownerUserIds:
            self.ownerUserIds.remove(user_id)
    
    def __str__(self):
        return f"{self.name} ({self.ref_id})" if self.ref_id else self.name

