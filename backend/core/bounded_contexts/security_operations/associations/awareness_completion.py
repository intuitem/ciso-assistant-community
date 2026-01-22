"""
AwarenessCompletion Association

First-class association representing a user's completion of an awareness activity.
"""

import uuid
from typing import Optional
from datetime import datetime
from django.db import models
from django.utils import timezone

from core.domain.aggregate import AggregateRoot
from ..domain_events import AwarenessCompletionRecorded


class AwarenessCompletion(AggregateRoot):
    """
    Awareness Completion association.
    
    First-class entity representing a user's completion of an awareness activity.
    """
    
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
    
    # Campaign reference
    campaignId = models.UUIDField(db_index=True, help_text="ID of the awareness campaign")
    
    # User reference
    userId = models.UUIDField(db_index=True, help_text="ID of the user")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
        db_index=True
    )
    
    # Completion
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Additional fields
    score = models.FloatField(null=True, blank=True, help_text="Completion score if applicable")
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = "security_operations_awareness_completions"
        verbose_name = "Awareness Completion"
        verbose_name_plural = "Awareness Completions"
        indexes = [
            models.Index(fields=["campaignId", "userId"]),
            models.Index(fields=["status"]),
            models.Index(fields=["completed_at"]),
        ]
        unique_together = [
            ["campaignId", "userId"]
        ]
    
    def create(self, campaign_id: uuid.UUID, user_id: uuid.UUID):
        """
        Create a new awareness completion record.
        
        Domain method that enforces business rules and raises events.
        """
        self.campaignId = campaign_id
        self.userId = user_id
        self.status = self.Status.NOT_STARTED
        
        # No event raised on creation, only on status changes
    
    def start(self):
        """Mark as in progress"""
        if self.status == self.Status.NOT_STARTED:
            self.status = self.Status.IN_PROGRESS
    
    def complete(self, score: float = None, notes: str = None):
        """Mark as completed"""
        if self.status != self.Status.COMPLETED:
            self.status = self.Status.COMPLETED
            self.completed_at = timezone.now()
            self.score = score
            self.notes = notes
            
            event = AwarenessCompletionRecorded()
            event.payload = {
                "completion_id": str(self.id),
                "campaign_id": str(self.campaignId),
                "user_id": str(self.userId),
                "score": score,
            }
            self._raise_event(event)
    
    def fail(self, notes: str = None):
        """Mark as failed"""
        if self.status != self.Status.FAILED:
            self.status = self.Status.FAILED
            self.notes = notes
    
    def __str__(self):
        return f"Completion for Campaign {self.campaignId} by User {self.userId} ({self.status})"

