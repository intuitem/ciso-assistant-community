"""
Group Aggregate

Represents a user group with permissions.
"""

import uuid
from typing import Optional, List
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    GroupCreated,
    PermissionAddedToGroup,
    UserAddedToGroup,
)


class Group(AggregateRoot):
    """
    Group aggregate root.
    
    Represents a user group with embedded permission and user IDs.
    """
    
    class LifecycleState(models.TextChoices):
        ACTIVE = "active", "Active"
        RETIRED = "retired", "Retired"
    
    # Basic fields
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.ACTIVE,
        db_index=True
    )
    
    # Embedded memberships (replacing ManyToMany)
    permissionIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of permission IDs"
    )
    userIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of user IDs in this group"
    )
    
    # Additional fields
    builtin = models.BooleanField(default=False, help_text="Built-in groups cannot be deleted")
    
    class Meta:
        db_table = "organization_groups"
        verbose_name = "Group"
        verbose_name_plural = "Groups"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["lifecycle_state"]),
        ]
    
    def create(self, name: str, description: str = None, builtin: bool = False):
        """
        Create a new group.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.description = description
        self.builtin = builtin
        self.lifecycle_state = self.LifecycleState.ACTIVE
        
        event = GroupCreated()
        event.payload = {
            "name": name,
            "builtin": builtin,
        }
        self._raise_event(event)
    
    def retire(self):
        """Retire the group"""
        if self.builtin:
            raise ValueError("Cannot retire built-in groups")
        
        if self.lifecycle_state != self.LifecycleState.RETIRED:
            self.lifecycle_state = self.LifecycleState.RETIRED
    
    def add_permission(self, permission_id: uuid.UUID):
        """
        Add a permission to this group.
        
        Args:
            permission_id: UUID of the permission
        """
        if permission_id not in self.permissionIds:
            self.permissionIds.append(permission_id)
            
            event = PermissionAddedToGroup()
            event.payload = {
                "group_id": str(self.id),
                "permission_id": str(permission_id),
            }
            self._raise_event(event)
    
    def add_user(self, user_id: uuid.UUID):
        """
        Add a user to this group.
        
        Args:
            user_id: UUID of the user
        """
        if user_id not in self.userIds:
            self.userIds.append(user_id)
            
            event = UserAddedToGroup()
            event.payload = {
                "group_id": str(self.id),
                "user_id": str(user_id),
            }
            self._raise_event(event)
    
    def remove_permission(self, permission_id: uuid.UUID):
        """Remove a permission from this group"""
        if permission_id in self.permissionIds:
            self.permissionIds.remove(permission_id)
    
    def remove_user(self, user_id: uuid.UUID):
        """Remove a user from this group"""
        if user_id in self.userIds:
            self.userIds.remove(user_id)
    
    def __str__(self):
        return self.name

