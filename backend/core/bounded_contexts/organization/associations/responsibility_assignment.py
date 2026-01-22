"""
ResponsibilityAssignment Association

First-class association representing responsibility assignments with role, scope, and dates.
"""

import uuid
from typing import Optional
from django.db import models
from django.core.exceptions import ValidationError

from core.domain.aggregate import AggregateRoot
from ..domain_events import (
    ResponsibilityAssigned,
    ResponsibilityRevoked,
)


class ResponsibilityAssignment(AggregateRoot):
    """
    Responsibility Assignment association.
    
    First-class entity representing a responsibility assignment with:
    - Subject (what the responsibility is for)
    - User (who has the responsibility)
    - Role (what role they have)
    - Scope (dates, etc.)
    """
    
    class SubjectType(models.TextChoices):
        ASSET = "asset", "Asset"
        PROCESS = "process", "Process"
        SERVICE = "service", "Service"
        RISK = "risk", "Risk"
        CONTROL = "control", "Control"
        POLICY = "policy", "Policy"
        PROJECT = "project", "Project"
        DATA_ASSET = "data_asset", "Data Asset"
        DATA_FLOW = "data_flow", "Data Flow"
        THIRD_PARTY = "third_party", "Third Party"
        ORG_UNIT = "org_unit", "Organizational Unit"
    
    # Subject (what the responsibility is for)
    subject_type = models.CharField(
        max_length=50,
        choices=SubjectType.choices,
        db_index=True
    )
    subject_id = models.UUIDField(db_index=True)
    
    # User (who has the responsibility)
    userId = models.UUIDField(db_index=True)
    
    # Role (what role they have)
    role = models.CharField(max_length=255, db_index=True)
    
    # Scope (dates)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Additional metadata
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = "organization_responsibility_assignments"
        verbose_name = "Responsibility Assignment"
        verbose_name_plural = "Responsibility Assignments"
        indexes = [
            models.Index(fields=["subject_type", "subject_id"]),
            models.Index(fields=["userId"]),
            models.Index(fields=["role"]),
        ]
        unique_together = [
            ["subject_type", "subject_id", "userId", "role"]
        ]
    
    def clean(self):
        """Validate assignment invariants"""
        super().clean()
        
        # Invariant: End date must be after start date
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError("End date must be after start date")
    
    def assign(self, subject_type: str, subject_id: uuid.UUID, user_id: uuid.UUID, 
               role: str, start_date=None, end_date=None, notes: str = None):
        """
        Create a responsibility assignment.
        
        Domain method that enforces business rules and raises events.
        """
        self.subject_type = subject_type
        self.subject_id = subject_id
        self.userId = user_id
        self.role = role
        self.start_date = start_date
        self.end_date = end_date
        self.notes = notes
        
        event = ResponsibilityAssigned()
        event.payload = {
            "assignment_id": str(self.id),
            "subject_type": subject_type,
            "subject_id": str(subject_id),
            "user_id": str(user_id),
            "role": role,
        }
        self._raise_event(event)
    
    def revoke(self):
        """Revoke this responsibility assignment"""
        if self.end_date is None:
            from django.utils import timezone
            self.end_date = timezone.now().date()
            
            event = ResponsibilityRevoked()
            event.payload = {
                "assignment_id": str(self.id),
                "revoked_at": str(self.end_date),
            }
            self._raise_event(event)
    
    def is_active(self) -> bool:
        """Check if assignment is currently active"""
        from django.utils import timezone
        today = timezone.now().date()
        
        if self.start_date and self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True
    
    def __str__(self):
        return f"{self.role} for {self.subject_type} {self.subject_id} (User: {self.userId})"

