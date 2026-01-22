"""
ComplianceException Association

First-class association representing a compliance exception.
"""

import uuid
from typing import Optional
from datetime import datetime
from django.db import models
from django.utils import timezone

from core.domain.aggregate import AggregateRoot
from ..domain_events import (
    ComplianceExceptionRequested,
    ComplianceExceptionApproved,
    ComplianceExceptionExpired,
    ComplianceExceptionRevoked,
)


class ComplianceException(AggregateRoot):
    """
    Compliance Exception association.
    
    First-class entity representing an exception to a compliance requirement.
    """
    
    class LifecycleState(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"
    
    # Requirement reference
    requirementId = models.UUIDField(db_index=True, help_text="ID of the requirement this exception applies to")
    
    # Basic fields
    reason = models.TextField(help_text="Reason for the exception")
    description = models.TextField(blank=True, null=True)
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.REQUESTED,
        db_index=True
    )
    
    # Approval
    approved_by_user_id = models.UUIDField(null=True, blank=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "compliance_compliance_exceptions"
        verbose_name = "Compliance Exception"
        verbose_name_plural = "Compliance Exceptions"
        indexes = [
            models.Index(fields=["requirementId", "lifecycle_state"]),
            models.Index(fields=["expires_at"]),
        ]
    
    def create(self, requirement_id: uuid.UUID, reason: str, description: str = None,
               expires_at: Optional[datetime] = None):
        """
        Create a new compliance exception.
        
        Domain method that enforces business rules and raises events.
        """
        self.requirementId = requirement_id
        self.reason = reason
        self.description = description
        self.expires_at = expires_at
        self.lifecycle_state = self.LifecycleState.REQUESTED
        
        event = ComplianceExceptionRequested()
        event.payload = {
            "exception_id": str(self.id),
            "requirement_id": str(requirement_id),
            "reason": reason,
        }
        self._raise_event(event)
    
    def approve(self, approved_by_user_id: uuid.UUID):
        """Approve the exception"""
        if self.lifecycle_state != self.LifecycleState.APPROVED:
            self.approved_by_user_id = approved_by_user_id
            self.lifecycle_state = self.LifecycleState.APPROVED
            
            event = ComplianceExceptionApproved()
            event.payload = {
                "exception_id": str(self.id),
                "requirement_id": str(self.requirementId),
                "approved_by_user_id": str(approved_by_user_id),
            }
            self._raise_event(event)
    
    def expire(self):
        """Mark the exception as expired"""
        if self.lifecycle_state != self.LifecycleState.EXPIRED:
            self.lifecycle_state = self.LifecycleState.EXPIRED
            
            event = ComplianceExceptionExpired()
            event.payload = {
                "exception_id": str(self.id),
                "requirement_id": str(self.requirementId),
            }
            self._raise_event(event)
    
    def revoke(self):
        """Revoke the exception"""
        if self.lifecycle_state != self.LifecycleState.REVOKED:
            self.lifecycle_state = self.LifecycleState.REVOKED
            
            event = ComplianceExceptionRevoked()
            event.payload = {
                "exception_id": str(self.id),
                "requirement_id": str(self.requirementId),
            }
            self._raise_event(event)
    
    def is_expired(self) -> bool:
        """Check if exception is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def __str__(self):
        return f"Exception for Requirement {self.requirementId} - {self.reason[:50]}"

