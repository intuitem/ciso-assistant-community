"""
Control Aggregate

Represents a control in the control library.
"""

import uuid
from typing import Optional, List
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    ControlCreated,
    ControlApproved,
    ControlDeprecated,
)


class Control(AggregateRoot):
    """
    Control aggregate root.
    
    Represents a control with embedded ID arrays for relationships.
    """
    
    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        DEPRECATED = "deprecated", "Deprecated"
    
    class ControlType(models.TextChoices):
        POLICY = "policy", "Policy"
        PROCESS = "process", "Process"
        TECHNICAL = "technical", "Technical"
        PHYSICAL = "physical", "Physical"
        PROCEDURE = "procedure", "Procedure"
    
    # Basic fields
    name = models.CharField(max_length=255, db_index=True)
    objective = models.TextField(blank=True, null=True)
    ref_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    
    # Type and domain
    control_type = models.CharField(
        max_length=20,
        choices=ControlType.choices,
        blank=True,
        null=True,
        db_index=True
    )
    domain = models.CharField(max_length=255, blank=True, null=True)
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.DRAFT,
        db_index=True
    )
    
    # Embedded ID arrays (replacing ManyToMany)
    legalRequirementIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of legal requirement IDs"
    )
    relatedControlIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of related control IDs"
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "control_library_controls"
        verbose_name = "Control"
        verbose_name_plural = "Controls"
        indexes = [
            models.Index(fields=["lifecycle_state", "control_type"]),
            models.Index(fields=["name"]),
            models.Index(fields=["ref_id"]),
        ]
    
    def create(self, name: str, objective: str = None, ref_id: str = None,
               control_type: str = None, domain: str = None):
        """
        Create a new control.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.objective = objective
        self.ref_id = ref_id
        self.control_type = control_type
        self.domain = domain
        self.lifecycle_state = self.LifecycleState.DRAFT
        
        event = ControlCreated()
        event.payload = {
            "name": name,
            "ref_id": ref_id,
            "control_type": control_type,
        }
        self._raise_event(event)
    
    def approve(self):
        """Approve the control"""
        if self.lifecycle_state != self.LifecycleState.APPROVED:
            self.lifecycle_state = self.LifecycleState.APPROVED
            
            event = ControlApproved()
            event.payload = {
                "control_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def deprecate(self):
        """Deprecate the control"""
        if self.lifecycle_state != self.LifecycleState.DEPRECATED:
            self.lifecycle_state = self.LifecycleState.DEPRECATED
            
            event = ControlDeprecated()
            event.payload = {
                "control_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def add_legal_requirement(self, requirement_id: uuid.UUID):
        """Add a legal requirement to this control"""
        if requirement_id not in self.legalRequirementIds:
            self.legalRequirementIds.append(requirement_id)
    
    def add_related_control(self, control_id: uuid.UUID):
        """Add a related control"""
        if control_id not in self.relatedControlIds:
            self.relatedControlIds.append(control_id)
    
    def __str__(self):
        return f"{self.ref_id} - {self.name}" if self.ref_id else self.name

