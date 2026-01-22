"""
User Aggregate

Represents a user in the organization.
"""

import uuid
from typing import Optional, List
from django.db import models
from django.contrib.auth.hashers import make_password

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    UserCreated,
    UserAssignedToGroup,
    UserAssignedToOrgUnit,
    UserActivated,
    UserDisabled,
)


class User(AggregateRoot):
    """
    User aggregate root.
    
    Represents a user in the organization with embedded group and org unit memberships.
    """
    
    class LifecycleState(models.TextChoices):
        INVITED = "invited", "Invited"
        ACTIVE = "active", "Active"
        DISABLED = "disabled", "Disabled"
    
    # Identity
    email = models.EmailField(unique=True, db_index=True)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    
    # Authentication
    password = models.CharField(max_length=128, blank=True, null=True)
    is_superuser = models.BooleanField(default=False)
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.INVITED,
        db_index=True
    )
    
    # Embedded memberships (replacing ManyToMany)
    groupIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of group IDs the user belongs to"
    )
    orgUnitIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of organizational unit IDs the user belongs to"
    )
    
    # Additional fields
    preferences = models.JSONField(default=dict, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    observation = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = "organization_users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["lifecycle_state"]),
        ]
    
    def create(self, email: str, display_name: str = None, password: str = None):
        """
        Create a new user.
        
        Domain method that enforces business rules and raises events.
        """
        self.email = email
        self.display_name = display_name or email.split("@")[0]
        self.lifecycle_state = self.LifecycleState.INVITED
        
        if password:
            self.password = make_password(password)
        
        event = UserCreated()
        event.payload = {
            "email": email,
            "display_name": display_name,
        }
        self._raise_event(event)
    
    def activate(self):
        """Activate the user"""
        if self.lifecycle_state != self.LifecycleState.ACTIVE:
            self.lifecycle_state = self.LifecycleState.ACTIVE
            
            event = UserActivated()
            event.payload = {
                "user_id": str(self.id),
                "email": self.email,
            }
            self._raise_event(event)
    
    def disable(self):
        """Disable the user"""
        if self.lifecycle_state != self.LifecycleState.DISABLED:
            self.lifecycle_state = self.LifecycleState.DISABLED
            
            event = UserDisabled()
            event.payload = {
                "user_id": str(self.id),
                "email": self.email,
            }
            self._raise_event(event)
    
    def assign_to_group(self, group_id: uuid.UUID):
        """
        Assign user to a group.
        
        Args:
            group_id: UUID of the group
        """
        if group_id not in self.groupIds:
            self.groupIds.append(group_id)
            
            event = UserAssignedToGroup()
            event.payload = {
                "user_id": str(self.id),
                "group_id": str(group_id),
            }
            self._raise_event(event)
    
    def assign_to_org_unit(self, org_unit_id: uuid.UUID):
        """
        Assign user to an organizational unit.
        
        Args:
            org_unit_id: UUID of the organizational unit
        """
        if org_unit_id not in self.orgUnitIds:
            self.orgUnitIds.append(org_unit_id)
            
            event = UserAssignedToOrgUnit()
            event.payload = {
                "user_id": str(self.id),
                "org_unit_id": str(org_unit_id),
            }
            self._raise_event(event)
    
    def remove_from_group(self, group_id: uuid.UUID):
        """Remove user from a group"""
        if group_id in self.groupIds:
            self.groupIds.remove(group_id)
    
    def remove_from_org_unit(self, org_unit_id: uuid.UUID):
        """Remove user from an organizational unit"""
        if org_unit_id in self.orgUnitIds:
            self.orgUnitIds.remove(org_unit_id)
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.display_name or self.email
    
    def __str__(self):
        return self.full_name or self.email

