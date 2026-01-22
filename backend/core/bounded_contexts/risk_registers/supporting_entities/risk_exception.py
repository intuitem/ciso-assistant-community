"""
RiskException Supporting Entity

Represents an exception to a risk.
"""

import uuid
from typing import Optional
from datetime import datetime
from django.db import models
from django.utils import timezone

from core.domain.aggregate import AggregateRoot
from ..domain_events import (
    RiskExceptionRequested,
    RiskExceptionApproved,
    RiskExceptionExpired,
    RiskExceptionRevoked,
)


class RiskException(AggregateRoot):
    """
    Risk Exception supporting entity.
    
    Represents an exception to a risk with approval workflow.
    """
    
    class LifecycleState(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"
    
    # Risk reference
    riskId = models.UUIDField(db_index=True, help_text="ID of the risk this exception applies to")
    
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
    approved_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "risk_registers_risk_exceptions"
        verbose_name = "Risk Exception"
        verbose_name_plural = "Risk Exceptions"
        indexes = [
            models.Index(fields=["riskId", "lifecycle_state"]),
            models.Index(fields=["expires_at"]),
        ]
    
    def create(self, risk_id: uuid.UUID, reason: str, description: str = None,
               expires_at: Optional[datetime] = None):
        """
        Create a new risk exception.
        
        Domain method that enforces business rules and raises events.
        """
        self.riskId = risk_id
        self.reason = reason
        self.description = description
        self.expires_at = expires_at
        self.lifecycle_state = self.LifecycleState.REQUESTED
        
        event = RiskExceptionRequested()
        event.payload = {
            "exception_id": str(self.id),
            "risk_id": str(risk_id),
            "reason": reason,
        }
        self._raise_event(event)
    
    def approve(self, approved_by_user_id: uuid.UUID):
        """Approve the exception"""
        if self.lifecycle_state != self.LifecycleState.APPROVED:
            self.approved_by_user_id = approved_by_user_id
            self.approved_at = timezone.now()
            self.lifecycle_state = self.LifecycleState.APPROVED
            
            event = RiskExceptionApproved()
            event.payload = {
                "exception_id": str(self.id),
                "risk_id": str(self.riskId),
                "approved_by_user_id": str(approved_by_user_id),
            }
            self._raise_event(event)
    
    def expire(self):
        """Mark the exception as expired"""
        if self.lifecycle_state != self.LifecycleState.EXPIRED:
            self.lifecycle_state = self.LifecycleState.EXPIRED
            
            event = RiskExceptionExpired()
            event.payload = {
                "exception_id": str(self.id),
                "risk_id": str(self.riskId),
            }
            self._raise_event(event)
    
    def revoke(self):
        """Revoke the exception"""
        if self.lifecycle_state != self.LifecycleState.REVOKED:
            self.lifecycle_state = self.LifecycleState.REVOKED
            
            event = RiskExceptionRevoked()
            event.payload = {
                "exception_id": str(self.id),
                "risk_id": str(self.riskId),
            }
            self._raise_event(event)
    
    def is_expired(self) -> bool:
        """Check if exception is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def __str__(self):
        return f"Exception for Risk {self.riskId} - {self.reason[:50]}"

