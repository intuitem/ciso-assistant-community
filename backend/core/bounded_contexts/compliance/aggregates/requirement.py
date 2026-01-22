"""
Requirement Aggregate

Represents a requirement within a compliance framework.
"""

import uuid
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    RequirementCreated,
    RequirementMappedToControl,
    RequirementRetired,
)


class Requirement(AggregateRoot):
    """
    Requirement aggregate root.
    
    Represents a requirement within a compliance framework.
    """
    
    class LifecycleState(models.TextChoices):
        ACTIVE = "active", "Active"
        RETIRED = "retired", "Retired"
    
    # Framework reference
    frameworkId = models.UUIDField(db_index=True, help_text="ID of the compliance framework")
    
    # Basic fields
    code = models.CharField(max_length=100, db_index=True, help_text="Requirement code (e.g., AC-1)")
    statement = models.TextField(help_text="Requirement statement")
    description = models.TextField(blank=True, null=True)
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.ACTIVE,
        db_index=True
    )
    
    # Embedded ID arrays (replacing ManyToMany)
    mappedControlIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of mapped control IDs"
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "compliance_requirements"
        verbose_name = "Requirement"
        verbose_name_plural = "Requirements"
        indexes = [
            models.Index(fields=["frameworkId", "code"]),
            models.Index(fields=["lifecycle_state"]),
        ]
        unique_together = [
            ["frameworkId", "code"]
        ]
    
    def create(self, framework_id: uuid.UUID, code: str, statement: str,
               description: str = None):
        """
        Create a new requirement.
        
        Domain method that enforces business rules and raises events.
        """
        self.frameworkId = framework_id
        self.code = code
        self.statement = statement
        self.description = description
        self.lifecycle_state = self.LifecycleState.ACTIVE
        
        event = RequirementCreated()
        event.payload = {
            "requirement_id": str(self.id),
            "framework_id": str(framework_id),
            "code": code,
        }
        self._raise_event(event)
    
    def map_to_control(self, control_id: uuid.UUID):
        """Map this requirement to a control"""
        if control_id not in self.mappedControlIds:
            self.mappedControlIds.append(control_id)
            
            event = RequirementMappedToControl()
            event.payload = {
                "requirement_id": str(self.id),
                "control_id": str(control_id),
            }
            self._raise_event(event)
    
    def retire(self):
        """Retire the requirement"""
        if self.lifecycle_state != self.LifecycleState.RETIRED:
            self.lifecycle_state = self.LifecycleState.RETIRED
            
            event = RequirementRetired()
            event.payload = {
                "requirement_id": str(self.id),
                "code": self.code,
            }
            self._raise_event(event)
    
    def __str__(self):
        return f"{self.code}: {self.statement[:50]}"

