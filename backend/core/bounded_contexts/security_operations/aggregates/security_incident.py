"""
SecurityIncident Aggregate

Represents a security incident with timeline tracking.
"""

import uuid
from typing import List, Optional
from datetime import datetime
from django.db import models
from django.utils import timezone

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..value_objects import IncidentEvent
from ..domain_events import (
    SecurityIncidentReported,
    SecurityIncidentTriaged,
    SecurityIncidentContained,
    SecurityIncidentEradicated,
    SecurityIncidentRecovered,
    SecurityIncidentClosed,
)


class SecurityIncident(AggregateRoot):
    """
    Security Incident aggregate root.
    
    Represents a security incident with lifecycle states and timeline tracking.
    """
    
    class LifecycleState(models.TextChoices):
        REPORTED = "reported", "Reported"
        TRIAGED = "triaged", "Triaged"
        CONTAINED = "contained", "Contained"
        ERADICATED = "eradicated", "Eradicated"
        RECOVERED = "recovered", "Recovered"
        CLOSED = "closed", "Closed"
    
    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"
    
    class DetectionSource(models.TextChoices):
        INTERNAL = "internal", "Internal"
        EXTERNAL = "external", "External"
    
    # Basic fields
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    # Classification
    classification_id = models.UUIDField(null=True, blank=True, db_index=True, help_text="ID of the incident classification")
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.REPORTED,
        db_index=True
    )
    
    # Severity and detection
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
        db_index=True
    )
    detection_source = models.CharField(
        max_length=20,
        choices=DetectionSource.choices,
        default=DetectionSource.INTERNAL,
        db_index=True
    )
    
    # Embedded ID arrays (replacing ManyToMany)
    affectedAssetIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of affected asset IDs"
    )
    affectedServiceIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of affected service IDs"
    )
    relatedRiskIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of related risk IDs"
    )
    evidenceIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of evidence IDs"
    )
    
    # Timeline (stored as JSON array of IncidentEvent value objects)
    timeline = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of timeline events: [{at, action, actorUserId, notes}]"
    )
    
    # Dates
    reported_at = models.DateTimeField(null=True, blank=True, db_index=True)
    triaged_at = models.DateTimeField(null=True, blank=True)
    contained_at = models.DateTimeField(null=True, blank=True)
    eradicated_at = models.DateTimeField(null=True, blank=True)
    recovered_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "security_operations_security_incidents"
        verbose_name = "Security Incident"
        verbose_name_plural = "Security Incidents"
        indexes = [
            models.Index(fields=["lifecycle_state", "severity"]),
            models.Index(fields=["reported_at"]),
        ]
    
    def create(self, title: str, description: str = None, severity: str = None,
               detection_source: str = None, classification_id: uuid.UUID = None):
        """
        Create a new security incident.
        
        Domain method that enforces business rules and raises events.
        """
        self.title = title
        self.description = description
        self.severity = severity or self.Severity.MEDIUM
        self.detection_source = detection_source or self.DetectionSource.INTERNAL
        self.classification_id = classification_id
        self.lifecycle_state = self.LifecycleState.REPORTED
        self.reported_at = timezone.now()
        
        # Add initial timeline event
        self.add_timeline_event("Incident reported", notes=description)
        
        event = SecurityIncidentReported()
        event.payload = {
            "incident_id": str(self.id),
            "title": title,
            "severity": self.severity,
        }
        self._raise_event(event)
    
    def triage(self, notes: str = None):
        """Triage the incident"""
        if self.lifecycle_state == self.LifecycleState.REPORTED:
            self.lifecycle_state = self.LifecycleState.TRIAGED
            self.triaged_at = timezone.now()
            self.add_timeline_event("Incident triaged", notes=notes)
            
            event = SecurityIncidentTriaged()
            event.payload = {
                "incident_id": str(self.id),
            }
            self._raise_event(event)
    
    def contain(self, notes: str = None):
        """Contain the incident"""
        if self.lifecycle_state in [self.LifecycleState.TRIAGED, self.LifecycleState.REPORTED]:
            self.lifecycle_state = self.LifecycleState.CONTAINED
            self.contained_at = timezone.now()
            self.add_timeline_event("Incident contained", notes=notes)
            
            event = SecurityIncidentContained()
            event.payload = {
                "incident_id": str(self.id),
            }
            self._raise_event(event)
    
    def eradicate(self, notes: str = None):
        """Eradicate the incident"""
        if self.lifecycle_state == self.LifecycleState.CONTAINED:
            self.lifecycle_state = self.LifecycleState.ERADICATED
            self.eradicated_at = timezone.now()
            self.add_timeline_event("Threat eradicated", notes=notes)
            
            event = SecurityIncidentEradicated()
            event.payload = {
                "incident_id": str(self.id),
            }
            self._raise_event(event)
    
    def recover(self, notes: str = None):
        """Recover from the incident"""
        if self.lifecycle_state == self.LifecycleState.ERADICATED:
            self.lifecycle_state = self.LifecycleState.RECOVERED
            self.recovered_at = timezone.now()
            self.add_timeline_event("Recovery complete", notes=notes)
            
            event = SecurityIncidentRecovered()
            event.payload = {
                "incident_id": str(self.id),
            }
            self._raise_event(event)
    
    def close(self, notes: str = None):
        """Close the incident"""
        if self.lifecycle_state != self.LifecycleState.CLOSED:
            self.lifecycle_state = self.LifecycleState.CLOSED
            self.closed_at = timezone.now()
            self.add_timeline_event("Incident closed", notes=notes)
            
            event = SecurityIncidentClosed()
            event.payload = {
                "incident_id": str(self.id),
            }
            self._raise_event(event)
    
    def add_timeline_event(self, action: str, actor_user_id: uuid.UUID = None,
                          notes: str = None):
        """Add an event to the timeline using IncidentEvent value object"""
        event = IncidentEvent.create(
            action=action,
            actor_user_id=str(actor_user_id) if actor_user_id else None,
            notes=notes,
        )
        self.timeline.append(event.to_dict())

    def get_timeline_events(self) -> List[IncidentEvent]:
        """Get timeline events as IncidentEvent value objects"""
        return [IncidentEvent.from_dict(e) for e in self.timeline]
    
    def add_affected_asset(self, asset_id: uuid.UUID):
        """Add an affected asset"""
        if asset_id not in self.affectedAssetIds:
            self.affectedAssetIds.append(asset_id)
    
    def add_affected_service(self, service_id: uuid.UUID):
        """Add an affected service"""
        if service_id not in self.affectedServiceIds:
            self.affectedServiceIds.append(service_id)
    
    def add_related_risk(self, risk_id: uuid.UUID):
        """Add a related risk"""
        if risk_id not in self.relatedRiskIds:
            self.relatedRiskIds.append(risk_id)
    
    def add_evidence(self, evidence_id: uuid.UUID):
        """Add evidence"""
        if evidence_id not in self.evidenceIds:
            self.evidenceIds.append(evidence_id)
    
    def __str__(self):
        return f"{self.title} ({self.severity})"

