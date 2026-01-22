"""
EvidenceItem Aggregate

Represents an evidence item in the control library.
"""

import uuid
from typing import Optional
from datetime import datetime
from django.db import models
from django.utils import timezone

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    EvidenceCollected,
    EvidenceVerified,
    EvidenceExpired,
)


class EvidenceItem(AggregateRoot):
    """
    Evidence Item aggregate root.
    
    Represents evidence with source type and lifecycle.
    """
    
    class LifecycleState(models.TextChoices):
        COLLECTED = "collected", "Collected"
        VERIFIED = "verified", "Verified"
        EXPIRED = "expired", "Expired"
    
    class SourceType(models.TextChoices):
        UPLOAD = "upload", "Upload"
        LINK = "link", "Link"
        SYSTEM_RECORD = "system_record", "System Record"
    
    # Basic fields
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    # Source type and lifecycle
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.UPLOAD,
        db_index=True
    )
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.COLLECTED,
        db_index=True
    )
    
    # URI and dates
    uri = models.URLField(max_length=2048, blank=True, null=True)
    collected_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Embedded ID arrays
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "control_library_evidence_items"
        verbose_name = "Evidence Item"
        verbose_name_plural = "Evidence Items"
        indexes = [
            models.Index(fields=["lifecycle_state", "source_type"]),
            models.Index(fields=["collected_at"]),
            models.Index(fields=["expires_at"]),
        ]
    
    def create(self, name: str, description: str = None, source_type: str = None,
               uri: str = None, expires_at: Optional[datetime] = None):
        """
        Create a new evidence item.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.description = description
        self.source_type = source_type or self.SourceType.UPLOAD
        self.uri = uri
        self.expires_at = expires_at
        self.lifecycle_state = self.LifecycleState.COLLECTED
        self.collected_at = timezone.now()
        
        event = EvidenceCollected()
        event.payload = {
            "evidence_id": str(self.id),
            "name": name,
            "source_type": self.source_type,
        }
        self._raise_event(event)
    
    def verify(self):
        """Verify the evidence"""
        if self.lifecycle_state != self.LifecycleState.VERIFIED:
            self.lifecycle_state = self.LifecycleState.VERIFIED
            
            event = EvidenceVerified()
            event.payload = {
                "evidence_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def expire(self):
        """Mark the evidence as expired"""
        if self.lifecycle_state != self.LifecycleState.EXPIRED:
            self.lifecycle_state = self.LifecycleState.EXPIRED
            
            event = EvidenceExpired()
            event.payload = {
                "evidence_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def is_expired(self) -> bool:
        """Check if evidence is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def __str__(self):
        return self.name

