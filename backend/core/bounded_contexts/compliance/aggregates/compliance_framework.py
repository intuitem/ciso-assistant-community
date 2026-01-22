"""
ComplianceFramework Aggregate

Represents a compliance framework (e.g., NIST 800-53, ISO 27001, GDPR).
"""

import uuid
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    ComplianceFrameworkCreated,
    ComplianceFrameworkActivated,
    ComplianceFrameworkRetired,
)


class ComplianceFramework(AggregateRoot):
    """
    Compliance Framework aggregate root.
    
    Represents a compliance framework with embedded ID arrays for requirements.
    """
    
    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        RETIRED = "retired", "Retired"
    
    # Basic fields
    name = models.CharField(max_length=255, db_index=True)
    version = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.DRAFT,
        db_index=True
    )
    
    # Embedded ID arrays (replacing ManyToMany)
    requirementIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of requirement IDs"
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "compliance_compliance_frameworks"
        verbose_name = "Compliance Framework"
        verbose_name_plural = "Compliance Frameworks"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["name", "version"]),
        ]
    
    def create(self, name: str, version: str = None, description: str = None):
        """
        Create a new compliance framework.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.version = version
        self.description = description
        self.lifecycle_state = self.LifecycleState.DRAFT
        
        event = ComplianceFrameworkCreated()
        event.payload = {
            "framework_id": str(self.id),
            "name": name,
            "version": version,
        }
        self._raise_event(event)
    
    def activate(self):
        """Activate the framework"""
        if self.lifecycle_state != self.LifecycleState.ACTIVE:
            self.lifecycle_state = self.LifecycleState.ACTIVE
            
            event = ComplianceFrameworkActivated()
            event.payload = {
                "framework_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def retire(self):
        """Retire the framework"""
        if self.lifecycle_state != self.LifecycleState.RETIRED:
            self.lifecycle_state = self.LifecycleState.RETIRED
            
            event = ComplianceFrameworkRetired()
            event.payload = {
                "framework_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def add_requirement(self, requirement_id: uuid.UUID):
        """Add a requirement to this framework"""
        if requirement_id not in self.requirementIds:
            self.requirementIds.append(requirement_id)
    
    def __str__(self):
        return f"{self.name} {self.version}" if self.version else self.name

