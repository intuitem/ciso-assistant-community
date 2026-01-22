"""
BcpTask Supporting Entity

Represents a task within a Business Continuity Plan.
"""

import uuid
from typing import Optional
from datetime import date
from django.db import models
from django.utils import timezone

from core.domain.aggregate import Entity
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    BcpTaskCreated,
    BcpTaskStatusChanged,
)


class BcpTask(Entity):
    """
    BCP Task supporting entity.
    
    Represents a task within a Business Continuity Plan.
    """
    
    class LifecycleState(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"
        BLOCKED = "blocked", "Blocked"
    
    # BCP reference
    bcpId = models.UUIDField(db_index=True, help_text="ID of the business continuity plan")
    
    # Basic fields
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.OPEN,
        db_index=True
    )
    
    # Assignment and dates
    owner_user_id = models.UUIDField(null=True, blank=True, db_index=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    
    # Evidence
    evidenceIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of evidence IDs"
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "business_continuity_bcp_tasks"
        verbose_name = "BCP Task"
        verbose_name_plural = "BCP Tasks"
        indexes = [
            models.Index(fields=["bcpId", "lifecycle_state"]),
            models.Index(fields=["due_date"]),
        ]
    
    def create(self, bcp_id: uuid.UUID, title: str, description: str = None,
               owner_user_id: uuid.UUID = None, due_date: Optional[date] = None):
        """
        Create a new BCP task.
        
        Domain method that enforces business rules and raises events.
        """
        self.bcpId = bcp_id
        self.title = title
        self.description = description
        self.owner_user_id = owner_user_id
        self.due_date = due_date
        self.lifecycle_state = self.LifecycleState.OPEN
        
        event = BcpTaskCreated()
        event.payload = {
            "task_id": str(self.id),
            "bcp_id": str(bcp_id),
            "title": title,
        }
        self._raise_event(event)
    
    def start(self):
        """Start the task"""
        if self.lifecycle_state != self.LifecycleState.IN_PROGRESS:
            old_state = self.lifecycle_state
            self.lifecycle_state = self.LifecycleState.IN_PROGRESS
            
            event = BcpTaskStatusChanged()
            event.payload = {
                "task_id": str(self.id),
                "old_state": old_state,
                "new_state": self.LifecycleState.IN_PROGRESS,
            }
            self._raise_event(event)
    
    def complete(self):
        """Complete the task"""
        if self.lifecycle_state != self.LifecycleState.DONE:
            old_state = self.lifecycle_state
            self.lifecycle_state = self.LifecycleState.DONE
            
            event = BcpTaskStatusChanged()
            event.payload = {
                "task_id": str(self.id),
                "old_state": old_state,
                "new_state": self.LifecycleState.DONE,
            }
            self._raise_event(event)
    
    def block(self):
        """Block the task"""
        if self.lifecycle_state != self.LifecycleState.BLOCKED:
            old_state = self.lifecycle_state
            self.lifecycle_state = self.LifecycleState.BLOCKED
            
            event = BcpTaskStatusChanged()
            event.payload = {
                "task_id": str(self.id),
                "old_state": old_state,
                "new_state": self.LifecycleState.BLOCKED,
            }
            self._raise_event(event)
    
    def add_evidence(self, evidence_id: uuid.UUID):
        """Add evidence"""
        if evidence_id not in self.evidenceIds:
            self.evidenceIds.append(evidence_id)
    
    def __str__(self):
        return f"{self.title} ({self.lifecycle_state})"

