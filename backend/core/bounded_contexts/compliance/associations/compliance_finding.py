"""
ComplianceFinding Association

First-class association representing a compliance finding.
"""

import uuid
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    ComplianceFindingCreated,
    ComplianceFindingStatusChanged,
)


class ComplianceFinding(AggregateRoot):
    """
    Compliance Finding association.
    
    First-class entity representing a compliance finding from audits, assessments, or reviews.
    """
    
    class LifecycleState(models.TextChoices):
        OPEN = "open", "Open"
        TRIAGED = "triaged", "Triaged"
        REMEDIATING = "remediating", "Remediating"
        VERIFIED = "verified", "Verified"
        CLOSED = "closed", "Closed"
    
    class SourceType(models.TextChoices):
        AUDIT = "audit", "Audit"
        ASSESSMENT = "assessment", "Assessment"
        INTERNAL_REVIEW = "internal_review", "Internal Review"
    
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"
    
    # Basic fields
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    # Source
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        db_index=True
    )
    source_id = models.UUIDField(db_index=True, help_text="ID of the source (audit, assessment, etc.)")
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.OPEN,
        db_index=True
    )
    
    # Severity
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
        db_index=True
    )
    
    # Embedded ID arrays
    requirementIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of requirement IDs"
    )
    controlImplementationIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of control implementation IDs"
    )
    remediationTaskIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of remediation task IDs"
    )
    evidenceIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of evidence IDs"
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "compliance_compliance_findings"
        verbose_name = "Compliance Finding"
        verbose_name_plural = "Compliance Findings"
        indexes = [
            models.Index(fields=["source_type", "source_id"]),
            models.Index(fields=["lifecycle_state", "severity"]),
        ]
    
    def create(self, title: str, source_type: str, source_id: uuid.UUID,
               description: str = None, severity: str = None):
        """
        Create a new compliance finding.
        
        Domain method that enforces business rules and raises events.
        """
        self.title = title
        self.description = description
        self.source_type = source_type
        self.source_id = source_id
        self.severity = severity or self.Severity.MEDIUM
        self.lifecycle_state = self.LifecycleState.OPEN
        
        event = ComplianceFindingCreated()
        event.payload = {
            "finding_id": str(self.id),
            "title": title,
            "source_type": source_type,
        }
        self._raise_event(event)
    
    def triage(self):
        """Triage the finding"""
        if self.lifecycle_state != self.LifecycleState.TRIAGED:
            old_state = self.lifecycle_state
            self.lifecycle_state = self.LifecycleState.TRIAGED
            
            event = ComplianceFindingStatusChanged()
            event.payload = {
                "finding_id": str(self.id),
                "old_state": old_state,
                "new_state": self.LifecycleState.TRIAGED,
            }
            self._raise_event(event)
    
    def start_remediation(self):
        """Start remediating the finding"""
        if self.lifecycle_state != self.LifecycleState.REMEDIATING:
            old_state = self.lifecycle_state
            self.lifecycle_state = self.LifecycleState.REMEDIATING
            
            event = ComplianceFindingStatusChanged()
            event.payload = {
                "finding_id": str(self.id),
                "old_state": old_state,
                "new_state": self.LifecycleState.REMEDIATING,
            }
            self._raise_event(event)
    
    def verify(self):
        """Verify the finding is resolved"""
        if self.lifecycle_state != self.LifecycleState.VERIFIED:
            old_state = self.lifecycle_state
            self.lifecycle_state = self.LifecycleState.VERIFIED
            
            event = ComplianceFindingStatusChanged()
            event.payload = {
                "finding_id": str(self.id),
                "old_state": old_state,
                "new_state": self.LifecycleState.VERIFIED,
            }
            self._raise_event(event)
    
    def close(self):
        """Close the finding"""
        if self.lifecycle_state != self.LifecycleState.CLOSED:
            old_state = self.lifecycle_state
            self.lifecycle_state = self.LifecycleState.CLOSED
            
            event = ComplianceFindingStatusChanged()
            event.payload = {
                "finding_id": str(self.id),
                "old_state": old_state,
                "new_state": self.LifecycleState.CLOSED,
            }
            self._raise_event(event)
    
    def add_requirement(self, requirement_id: uuid.UUID):
        """Add a requirement to this finding"""
        if requirement_id not in self.requirementIds:
            self.requirementIds.append(requirement_id)
    
    def add_control_implementation(self, implementation_id: uuid.UUID):
        """Add a control implementation to this finding"""
        if implementation_id not in self.controlImplementationIds:
            self.controlImplementationIds.append(implementation_id)
    
    def add_remediation_task(self, task_id: uuid.UUID):
        """Add a remediation task to this finding"""
        if task_id not in self.remediationTaskIds:
            self.remediationTaskIds.append(task_id)
    
    def add_evidence(self, evidence_id: uuid.UUID):
        """Add evidence to this finding"""
        if evidence_id not in self.evidenceIds:
            self.evidenceIds.append(evidence_id)
    
    def __str__(self):
        return f"{self.title} ({self.severity})"

