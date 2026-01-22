"""
ControlImplementation Association

First-class association representing the implementation of a control on a target.
"""

import uuid
from typing import Optional
from datetime import datetime
from django.db import models
from django.utils import timezone

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    ControlImplementationCreated,
    ControlImplementationStatusChanged,
    ControlImplementationTested,
)


class ControlImplementation(AggregateRoot):
    """
    Control Implementation association.
    
    First-class entity representing the implementation of a control on a target
    with status, evidence, frequency, and effectiveness tracking.
    """
    
    class LifecycleState(models.TextChoices):
        PLANNED = "planned", "Planned"
        IMPLEMENTED = "implemented", "Implemented"
        OPERATING = "operating", "Operating"
        INEFFECTIVE = "ineffective", "Ineffective"
        RETIRED = "retired", "Retired"
    
    class TargetType(models.TextChoices):
        ASSET = "asset", "Asset"
        SERVICE = "service", "Service"
        PROCESS = "process", "Process"
        THIRD_PARTY = "third_party", "Third Party"
        ORG_UNIT = "org_unit", "Organizational Unit"
        DATA_FLOW = "data_flow", "Data Flow"
        DATA_ASSET = "data_asset", "Data Asset"
    
    class Frequency(models.TextChoices):
        AD_HOC = "ad_hoc", "Ad Hoc"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUALLY = "annually", "Annually"
    
    # Control and target
    controlId = models.UUIDField(db_index=True)
    target_type = models.CharField(
        max_length=50,
        choices=TargetType.choices,
        db_index=True
    )
    target_id = models.UUIDField(db_index=True)
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.PLANNED,
        db_index=True
    )
    
    # Embedded ID arrays
    ownerUserIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of owner user IDs"
    )
    evidenceIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of evidence IDs"
    )
    
    # Frequency and testing
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.AD_HOC,
        db_index=True
    )
    last_tested_at = models.DateTimeField(null=True, blank=True, db_index=True)
    effectiveness_rating = models.IntegerField(
        null=True,
        blank=True,
        help_text="Effectiveness rating (1-5)"
    )
    
    # Additional fields
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = "control_library_control_implementations"
        verbose_name = "Control Implementation"
        verbose_name_plural = "Control Implementations"
        indexes = [
            models.Index(fields=["controlId", "target_type", "target_id"]),
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["last_tested_at"]),
        ]
        unique_together = [
            ["controlId", "target_type", "target_id"]
        ]
    
    def create(self, control_id: uuid.UUID, target_type: str, target_id: uuid.UUID,
               frequency: str = None, owner_user_ids: list = None):
        """
        Create a new control implementation.
        
        Domain method that enforces business rules and raises events.
        """
        self.controlId = control_id
        self.target_type = target_type
        self.target_id = target_id
        self.frequency = frequency or self.Frequency.AD_HOC
        self.ownerUserIds = owner_user_ids or []
        self.lifecycle_state = self.LifecycleState.PLANNED
        
        event = ControlImplementationCreated()
        event.payload = {
            "implementation_id": str(self.id),
            "control_id": str(control_id),
            "target_type": target_type,
            "target_id": str(target_id),
        }
        self._raise_event(event)
    
    def mark_implemented(self):
        """Mark the implementation as implemented"""
        if self.lifecycle_state != self.LifecycleState.IMPLEMENTED:
            old_state = self.lifecycle_state
            self.lifecycle_state = self.LifecycleState.IMPLEMENTED
            
            event = ControlImplementationStatusChanged()
            event.payload = {
                "implementation_id": str(self.id),
                "old_state": old_state,
                "new_state": self.LifecycleState.IMPLEMENTED,
            }
            self._raise_event(event)
    
    def mark_operating(self):
        """Mark the implementation as operating"""
        if self.lifecycle_state != self.LifecycleState.OPERATING:
            old_state = self.lifecycle_state
            self.lifecycle_state = self.LifecycleState.OPERATING
            
            event = ControlImplementationStatusChanged()
            event.payload = {
                "implementation_id": str(self.id),
                "old_state": old_state,
                "new_state": self.LifecycleState.OPERATING,
            }
            self._raise_event(event)
    
    def mark_ineffective(self):
        """Mark the implementation as ineffective"""
        if self.lifecycle_state != self.LifecycleState.INEFFECTIVE:
            old_state = self.lifecycle_state
            self.lifecycle_state = self.LifecycleState.INEFFECTIVE
            
            event = ControlImplementationStatusChanged()
            event.payload = {
                "implementation_id": str(self.id),
                "old_state": old_state,
                "new_state": self.LifecycleState.INEFFECTIVE,
            }
            self._raise_event(event)
    
    def record_test(self, effectiveness_rating: int, tested_at: Optional[datetime] = None):
        """
        Record a test of the control implementation.
        
        Args:
            effectiveness_rating: Rating from 1-5
            tested_at: When the test was performed (defaults to now)
        """
        if not (1 <= effectiveness_rating <= 5):
            raise ValueError("Effectiveness rating must be between 1 and 5")
        
        self.last_tested_at = tested_at or timezone.now()
        self.effectiveness_rating = effectiveness_rating
        
        # If tested and effective, mark as operating
        if effectiveness_rating >= 3 and self.lifecycle_state == self.LifecycleState.IMPLEMENTED:
            self.mark_operating()
        
        event = ControlImplementationTested()
        event.payload = {
            "implementation_id": str(self.id),
            "effectiveness_rating": effectiveness_rating,
            "tested_at": str(self.last_tested_at),
        }
        self._raise_event(event)
    
    def add_evidence(self, evidence_id: uuid.UUID):
        """Add evidence to this implementation"""
        if evidence_id not in self.evidenceIds:
            self.evidenceIds.append(evidence_id)
    
    def assign_owner(self, user_id: uuid.UUID):
        """Assign an owner to this implementation"""
        if user_id not in self.ownerUserIds:
            self.ownerUserIds.append(user_id)
    
    def __str__(self):
        return f"Control {self.controlId} on {self.target_type} {self.target_id} ({self.lifecycle_state})"

