"""
Process Aggregate

Represents a business process in the organization.
"""

import uuid
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    ProcessCreated,
    ProcessActivated,
    ProcessRetired,
)


class Process(AggregateRoot):
    """
    Process aggregate root.
    
    Represents a business process with embedded ID arrays for relationships.
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
    
    # Embedded ID arrays (replacing ManyToMany)
    orgUnitIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of organizational unit IDs"
    )
    assetIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of asset IDs"
    )
    controlIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of control IDs"
    )
    riskIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of risk IDs"
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "asset_service_processes"
        verbose_name = "Process"
        verbose_name_plural = "Processes"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["name"]),
            models.Index(fields=["ref_id"]),
        ]
    
    def create(self, name: str, description: str = None, ref_id: str = None):
        """
        Create a new process.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.description = description
        self.ref_id = ref_id
        self.lifecycle_state = self.LifecycleState.DRAFT
        
        event = ProcessCreated()
        event.payload = {
            "name": name,
            "ref_id": ref_id,
        }
        self._raise_event(event)
    
    def activate(self):
        """Activate the process"""
        if self.lifecycle_state != self.LifecycleState.ACTIVE:
            self.lifecycle_state = self.LifecycleState.ACTIVE
            
            event = ProcessActivated()
            event.payload = {
                "process_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def retire(self):
        """Retire the process"""
        if self.lifecycle_state != self.LifecycleState.RETIRED:
            self.lifecycle_state = self.LifecycleState.RETIRED
            
            event = ProcessRetired()
            event.payload = {
                "process_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def assign_to_org_unit(self, org_unit_id: uuid.UUID):
        """Assign this process to an organizational unit"""
        if org_unit_id not in self.orgUnitIds:
            self.orgUnitIds.append(org_unit_id)
    
    def link_asset(self, asset_id: uuid.UUID):
        """Link an asset to this process"""
        if asset_id not in self.assetIds:
            self.assetIds.append(asset_id)
    
    def assign_control(self, control_id: uuid.UUID):
        """Assign a control to this process"""
        if control_id not in self.controlIds:
            self.controlIds.append(control_id)
    
    def assign_risk(self, risk_id: uuid.UUID):
        """Assign a risk to this process"""
        if risk_id not in self.riskIds:
            self.riskIds.append(risk_id)
    
    def __str__(self):
        return f"{self.name} ({self.ref_id})" if self.ref_id else self.name

