"""
BusinessContinuityPlan Aggregate

Represents a Business Continuity Plan (BCP/DR plan).
"""

import uuid
from typing import List
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    BusinessContinuityPlanCreated,
    BusinessContinuityPlanApproved,
    BusinessContinuityPlanExercised,
    BusinessContinuityPlanRetired,
)


class BusinessContinuityPlan(AggregateRoot):
    """
    Business Continuity Plan aggregate root.
    
    Represents a BCP/DR plan with tasks and audit trail.
    """
    
    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        EXERCISED = "exercised", "Exercised"
        RETIRED = "retired", "Retired"
    
    # Basic fields
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    
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
    processIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of process IDs"
    )
    assetIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of asset IDs"
    )
    serviceIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of service IDs"
    )
    taskIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of BCP task IDs"
    )
    auditIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of BCP audit IDs"
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "business_continuity_business_continuity_plans"
        verbose_name = "Business Continuity Plan"
        verbose_name_plural = "Business Continuity Plans"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["name"]),
        ]
    
    def create(self, name: str, description: str = None):
        """
        Create a new business continuity plan.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.description = description
        self.lifecycle_state = self.LifecycleState.DRAFT
        
        event = BusinessContinuityPlanCreated()
        event.payload = {
            "bcp_id": str(self.id),
            "name": name,
        }
        self._raise_event(event)
    
    def approve(self):
        """Approve the BCP"""
        if self.lifecycle_state != self.LifecycleState.APPROVED:
            self.lifecycle_state = self.LifecycleState.APPROVED
            
            event = BusinessContinuityPlanApproved()
            event.payload = {
                "bcp_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def exercise(self):
        """Mark the BCP as exercised (tested)"""
        if self.lifecycle_state != self.LifecycleState.EXERCISED:
            self.lifecycle_state = self.LifecycleState.EXERCISED
            
            event = BusinessContinuityPlanExercised()
            event.payload = {
                "bcp_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def retire(self):
        """Retire the BCP"""
        if self.lifecycle_state != self.LifecycleState.RETIRED:
            self.lifecycle_state = self.LifecycleState.RETIRED
            
            event = BusinessContinuityPlanRetired()
            event.payload = {
                "bcp_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def add_org_unit(self, org_unit_id: uuid.UUID):
        """Add an organizational unit"""
        if org_unit_id not in self.orgUnitIds:
            self.orgUnitIds.append(org_unit_id)
    
    def add_process(self, process_id: uuid.UUID):
        """Add a process"""
        if process_id not in self.processIds:
            self.processIds.append(process_id)
    
    def add_asset(self, asset_id: uuid.UUID):
        """Add an asset"""
        if asset_id not in self.assetIds:
            self.assetIds.append(asset_id)
    
    def add_service(self, service_id: uuid.UUID):
        """Add a service"""
        if service_id not in self.serviceIds:
            self.serviceIds.append(service_id)
    
    def add_task(self, task_id: uuid.UUID):
        """Add a task"""
        if task_id not in self.taskIds:
            self.taskIds.append(task_id)
    
    def add_audit(self, audit_id: uuid.UUID):
        """Add an audit"""
        if audit_id not in self.auditIds:
            self.auditIds.append(audit_id)
    
    def __str__(self):
        return self.name

