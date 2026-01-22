"""
AwarenessProgram Aggregate

Represents a security awareness program.
"""

import uuid
from typing import List, Optional
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    AwarenessProgramCreated,
    AwarenessProgramActivated,
    AwarenessProgramPaused,
    AwarenessProgramRetired,
)


class AwarenessProgram(AggregateRoot):
    """
    Awareness Program aggregate root.
    
    Represents a security awareness program with campaigns.
    """
    
    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
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
    audienceOrgUnitIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of audience organizational unit IDs"
    )
    policyIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of related policy IDs"
    )
    campaignIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of campaign IDs"
    )
    
    # Cadence
    cadence_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Cadence in days (e.g., 30 for monthly)"
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "security_operations_awareness_programs"
        verbose_name = "Awareness Program"
        verbose_name_plural = "Awareness Programs"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["name"]),
        ]
    
    def create(self, name: str, description: str = None, cadence_days: int = None):
        """
        Create a new awareness program.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.description = description
        self.cadence_days = cadence_days
        self.lifecycle_state = self.LifecycleState.DRAFT
        
        event = AwarenessProgramCreated()
        event.payload = {
            "program_id": str(self.id),
            "name": name,
        }
        self._raise_event(event)
    
    def activate(self):
        """Activate the program"""
        if self.lifecycle_state != self.LifecycleState.ACTIVE:
            self.lifecycle_state = self.LifecycleState.ACTIVE
            
            event = AwarenessProgramActivated()
            event.payload = {
                "program_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def pause(self):
        """Pause the program"""
        if self.lifecycle_state != self.LifecycleState.PAUSED:
            self.lifecycle_state = self.LifecycleState.PAUSED
            
            event = AwarenessProgramPaused()
            event.payload = {
                "program_id": str(self.id),
            }
            self._raise_event(event)
    
    def retire(self):
        """Retire the program"""
        if self.lifecycle_state != self.LifecycleState.RETIRED:
            self.lifecycle_state = self.LifecycleState.RETIRED
            
            event = AwarenessProgramRetired()
            event.payload = {
                "program_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def add_audience_org_unit(self, org_unit_id: uuid.UUID):
        """Add an audience organizational unit"""
        if org_unit_id not in self.audienceOrgUnitIds:
            self.audienceOrgUnitIds.append(org_unit_id)
    
    def add_policy(self, policy_id: uuid.UUID):
        """Add a related policy"""
        if policy_id not in self.policyIds:
            self.policyIds.append(policy_id)
    
    def add_campaign(self, campaign_id: uuid.UUID):
        """Add a campaign"""
        if campaign_id not in self.campaignIds:
            self.campaignIds.append(campaign_id)
    
    def __str__(self):
        return self.name

