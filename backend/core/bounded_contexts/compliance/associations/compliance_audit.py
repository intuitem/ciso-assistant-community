"""
ComplianceAudit Association

First-class association representing a compliance audit.
"""

import uuid
from typing import Optional
from datetime import date
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    ComplianceAuditCreated,
    ComplianceAuditStarted,
    ComplianceAuditCompleted,
    ComplianceAuditClosed,
)


class ComplianceAudit(AggregateRoot):
    """
    Compliance Audit association.
    
    First-class entity representing a compliance audit with scope, auditor, dates, and findings.
    """
    
    class LifecycleState(models.TextChoices):
        PLANNED = "planned", "Planned"
        RUNNING = "running", "Running"
        REPORTED = "reported", "Reported"
        CLOSED = "closed", "Closed"
    
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
    
    # Scope
    scopeFrameworkIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of framework IDs in scope"
    )
    scopeRequirementIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of requirement IDs in scope"
    )
    
    # Auditor and dates
    auditor_org = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    
    # Findings
    findingIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of finding IDs"
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "compliance_compliance_audits"
        verbose_name = "Compliance Audit"
        verbose_name_plural = "Compliance Audits"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["start_date"]),
            models.Index(fields=["auditor_org"]),
        ]
    
    def create(self, name: str, start_date: date, description: str = None,
               auditor_org: str = None, end_date: Optional[date] = None,
               scope_framework_ids: List[uuid.UUID] = None,
               scope_requirement_ids: List[uuid.UUID] = None):
        """
        Create a new compliance audit.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.description = description
        self.auditor_org = auditor_org
        self.start_date = start_date
        self.end_date = end_date
        self.scopeFrameworkIds = scope_framework_ids or []
        self.scopeRequirementIds = scope_requirement_ids or []
        self.lifecycle_state = self.LifecycleState.PLANNED
        
        event = ComplianceAuditCreated()
        event.payload = {
            "audit_id": str(self.id),
            "name": name,
            "start_date": str(start_date),
        }
        self._raise_event(event)
    
    def start(self):
        """Start the audit"""
        if self.lifecycle_state != self.LifecycleState.RUNNING:
            self.lifecycle_state = self.LifecycleState.RUNNING
            
            event = ComplianceAuditStarted()
            event.payload = {
                "audit_id": str(self.id),
            }
            self._raise_event(event)
    
    def complete(self, end_date: Optional[date] = None):
        """Complete the audit"""
        if self.lifecycle_state != self.LifecycleState.REPORTED:
            if end_date:
                self.end_date = end_date
            
            self.lifecycle_state = self.LifecycleState.REPORTED
            
            event = ComplianceAuditCompleted()
            event.payload = {
                "audit_id": str(self.id),
            }
            self._raise_event(event)
    
    def close(self):
        """Close the audit"""
        if self.lifecycle_state != self.LifecycleState.CLOSED:
            self.lifecycle_state = self.LifecycleState.CLOSED
            
            event = ComplianceAuditClosed()
            event.payload = {
                "audit_id": str(self.id),
            }
            self._raise_event(event)
    
    def add_finding(self, finding_id: uuid.UUID):
        """Add a finding to this audit"""
        if finding_id not in self.findingIds:
            self.findingIds.append(finding_id)
    
    def add_scope_framework(self, framework_id: uuid.UUID):
        """Add a framework to the audit scope"""
        if framework_id not in self.scopeFrameworkIds:
            self.scopeFrameworkIds.append(framework_id)
    
    def add_scope_requirement(self, requirement_id: uuid.UUID):
        """Add a requirement to the audit scope"""
        if requirement_id not in self.scopeRequirementIds:
            self.scopeRequirementIds.append(requirement_id)
    
    def __str__(self):
        return f"{self.name} ({self.lifecycle_state})"

