"""
AwarenessCampaign Association

First-class association representing a campaign within an awareness program.
"""

import uuid
from typing import List, Optional
from datetime import date
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    AwarenessCampaignCreated,
    AwarenessCampaignStarted,
    AwarenessCampaignCompleted,
    AwarenessCampaignCancelled,
)


class AwarenessCampaign(AggregateRoot):
    """
    Awareness Campaign association.
    
    First-class entity representing a campaign with scheduling, completion metrics, and per-user state.
    """
    
    class LifecycleState(models.TextChoices):
        PLANNED = "planned", "Planned"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
    
    # Program reference
    programId = models.UUIDField(db_index=True, help_text="ID of the awareness program")
    
    # Basic fields
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.PLANNED,
        db_index=True
    )
    
    # Scheduling
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    
    # Embedded ID arrays
    targetUserIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of target user IDs"
    )
    completionIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of completion IDs"
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "security_operations_awareness_campaigns"
        verbose_name = "Awareness Campaign"
        verbose_name_plural = "Awareness Campaigns"
        indexes = [
            models.Index(fields=["programId", "lifecycle_state"]),
            models.Index(fields=["start_date"]),
        ]
    
    def create(self, program_id: uuid.UUID, name: str, start_date: date,
               description: str = None, end_date: Optional[date] = None):
        """
        Create a new awareness campaign.
        
        Domain method that enforces business rules and raises events.
        """
        self.programId = program_id
        self.name = name
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.lifecycle_state = self.LifecycleState.PLANNED
        
        event = AwarenessCampaignCreated()
        event.payload = {
            "campaign_id": str(self.id),
            "program_id": str(program_id),
            "name": name,
        }
        self._raise_event(event)
    
    def start(self):
        """Start the campaign"""
        if self.lifecycle_state != self.LifecycleState.RUNNING:
            self.lifecycle_state = self.LifecycleState.RUNNING
            
            event = AwarenessCampaignStarted()
            event.payload = {
                "campaign_id": str(self.id),
            }
            self._raise_event(event)
    
    def complete(self, end_date: Optional[date] = None):
        """Complete the campaign"""
        if self.lifecycle_state != self.LifecycleState.COMPLETED:
            if end_date:
                self.end_date = end_date
            
            self.lifecycle_state = self.LifecycleState.COMPLETED
            
            event = AwarenessCampaignCompleted()
            event.payload = {
                "campaign_id": str(self.id),
            }
            self._raise_event(event)
    
    def cancel(self):
        """Cancel the campaign"""
        if self.lifecycle_state != self.LifecycleState.CANCELLED:
            self.lifecycle_state = self.LifecycleState.CANCELLED
            
            event = AwarenessCampaignCancelled()
            event.payload = {
                "campaign_id": str(self.id),
            }
            self._raise_event(event)
    
    def add_target_user(self, user_id: uuid.UUID):
        """Add a target user"""
        if user_id not in self.targetUserIds:
            self.targetUserIds.append(user_id)
    
    def add_completion(self, completion_id: uuid.UUID):
        """Add a completion record"""
        if completion_id not in self.completionIds:
            self.completionIds.append(completion_id)
    
    def __str__(self):
        return f"{self.name} ({self.start_date})"

