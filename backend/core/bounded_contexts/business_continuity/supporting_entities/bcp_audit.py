"""
BcpAudit Supporting Entity

Represents an audit of a Business Continuity Plan.
"""

import uuid
from typing import Optional
from datetime import datetime
from django.db import models

from core.domain.aggregate import Entity
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    BcpAuditCreated,
    BcpAuditCompleted,
)


class BcpAudit(Entity):
    """
    BCP Audit supporting entity.
    
    Represents an audit of a Business Continuity Plan.
    """
    
    class LifecycleState(models.TextChoices):
        PLANNED = "planned", "Planned"
        RUNNING = "running", "Running"
        REPORTED = "reported", "Reported"
        CLOSED = "closed", "Closed"
    
    class Outcome(models.TextChoices):
        PASS = "pass", "Pass"
        FAIL = "fail", "Fail"
        PARTIAL = "partial", "Partial"
    
    # BCP reference
    bcpId = models.UUIDField(db_index=True, help_text="ID of the business continuity plan")
    
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
    
    # Audit details
    performed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    outcome = models.CharField(
        max_length=20,
        choices=Outcome.choices,
        null=True,
        blank=True,
        db_index=True
    )
    notes = models.TextField(blank=True, null=True)
    
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
        db_table = "business_continuity_bcp_audits"
        verbose_name = "BCP Audit"
        verbose_name_plural = "BCP Audits"
        indexes = [
            models.Index(fields=["bcpId", "lifecycle_state"]),
            models.Index(fields=["performed_at"]),
        ]
    
    def create(self, bcp_id: uuid.UUID, name: str, description: str = None):
        """
        Create a new BCP audit.
        
        Domain method that enforces business rules and raises events.
        """
        self.bcpId = bcp_id
        self.name = name
        self.description = description
        self.lifecycle_state = self.LifecycleState.PLANNED
        
        event = BcpAuditCreated()
        event.payload = {
            "audit_id": str(self.id),
            "bcp_id": str(bcp_id),
            "name": name,
        }
        self._raise_event(event)
    
    def start(self, performed_at: Optional[datetime] = None):
        """Start the audit"""
        if self.lifecycle_state != self.LifecycleState.RUNNING:
            self.lifecycle_state = self.LifecycleState.RUNNING
            if performed_at:
                self.performed_at = performed_at
    
    def complete(self, outcome: str, notes: str = None):
        """Complete the audit"""
        if self.lifecycle_state != self.LifecycleState.REPORTED:
            self.lifecycle_state = self.LifecycleState.REPORTED
            self.outcome = outcome
            self.notes = notes
            
            event = BcpAuditCompleted()
            event.payload = {
                "audit_id": str(self.id),
                "bcp_id": str(self.bcpId),
                "outcome": outcome,
            }
            self._raise_event(event)
    
    def close(self):
        """Close the audit"""
        if self.lifecycle_state != self.LifecycleState.CLOSED:
            self.lifecycle_state = self.LifecycleState.CLOSED
    
    def add_evidence(self, evidence_id: uuid.UUID):
        """Add evidence"""
        if evidence_id not in self.evidenceIds:
            self.evidenceIds.append(evidence_id)
    
    def __str__(self):
        return f"{self.name} ({self.outcome or 'Pending'})"

