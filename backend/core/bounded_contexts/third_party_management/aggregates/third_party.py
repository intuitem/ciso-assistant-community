"""
ThirdParty Aggregate

Represents a third party (supplier, vendor, partner).
"""

import uuid
from typing import List, Optional
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    ThirdPartyCreated,
    ThirdPartyActivated,
    ThirdPartyOffboardingStarted,
    ThirdPartyArchived,
    ThirdPartyLifecycleChanged,
)


class ThirdParty(AggregateRoot):
    """
    Third Party aggregate root.
    
    Represents a third party with lifecycle states and relationships.
    """
    
    class LifecycleState(models.TextChoices):
        PROSPECT = "prospect", "Prospect"
        ACTIVE = "active", "Active"
        OFFBOARDING = "offboarding", "Offboarding"
        ARCHIVED = "archived", "Archived"
    
    class Criticality(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"
    
    # Basic fields
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    # Criticality
    criticality = models.CharField(
        max_length=20,
        choices=Criticality.choices,
        default=Criticality.MEDIUM,
        db_index=True
    )
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.PROSPECT,
        db_index=True
    )
    
    # Embedded ID arrays (replacing ManyToMany)
    serviceIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of service IDs provided by this third party"
    )
    contractIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of contract IDs"
    )
    assessmentRunIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of assessment run IDs"
    )
    riskIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of risk IDs"
    )
    controlImplementationIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of control implementation IDs"
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "third_party_management_third_parties"
        verbose_name = "Third Party"
        verbose_name_plural = "Third Parties"
        indexes = [
            models.Index(fields=["lifecycle_state", "criticality"]),
            models.Index(fields=["name"]),
        ]
    
    def create(self, name: str, description: str = None,
               criticality: str = None):
        """
        Create a new third party.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.description = description
        self.criticality = criticality or self.Criticality.MEDIUM
        self.lifecycle_state = self.LifecycleState.PROSPECT
        
        event = ThirdPartyCreated()
        event.payload = {
            "third_party_id": str(self.id),
            "name": name,
            "criticality": self.criticality,
        }
        self._raise_event(event)
    
    def activate(self):
        """Activate the third party"""
        if self.lifecycle_state != self.LifecycleState.ACTIVE:
            old_state = self.lifecycle_state
            self.lifecycle_state = self.LifecycleState.ACTIVE
            
            event = ThirdPartyActivated()
            event.payload = {
                "third_party_id": str(self.id),
                "name": self.name,
                "old_state": old_state,
                "new_state": self.LifecycleState.ACTIVE,
            }
            self._raise_event(event)
            
            # Also raise lifecycle changed event
            lifecycle_event = ThirdPartyLifecycleChanged()
            lifecycle_event.payload = {
                "third_party_id": str(self.id),
                "old_state": old_state,
                "new_state": self.LifecycleState.ACTIVE,
            }
            self._raise_event(lifecycle_event)
    
    def start_offboarding(self):
        """Start offboarding the third party"""
        if self.lifecycle_state != self.LifecycleState.OFFBOARDING:
            old_state = self.lifecycle_state
            self.lifecycle_state = self.LifecycleState.OFFBOARDING
            
            event = ThirdPartyOffboardingStarted()
            event.payload = {
                "third_party_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
            
            # Also raise lifecycle changed event
            lifecycle_event = ThirdPartyLifecycleChanged()
            lifecycle_event.payload = {
                "third_party_id": str(self.id),
                "old_state": old_state,
                "new_state": self.LifecycleState.OFFBOARDING,
            }
            self._raise_event(lifecycle_event)
    
    def archive(self):
        """Archive the third party"""
        if self.lifecycle_state != self.LifecycleState.ARCHIVED:
            old_state = self.lifecycle_state
            self.lifecycle_state = self.LifecycleState.ARCHIVED
            
            event = ThirdPartyArchived()
            event.payload = {
                "third_party_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
            
            # Also raise lifecycle changed event
            lifecycle_event = ThirdPartyLifecycleChanged()
            lifecycle_event.payload = {
                "third_party_id": str(self.id),
                "old_state": old_state,
                "new_state": self.LifecycleState.ARCHIVED,
            }
            self._raise_event(lifecycle_event)
    
    def add_service(self, service_id: uuid.UUID):
        """Add a service provided by this third party"""
        if service_id not in self.serviceIds:
            self.serviceIds.append(service_id)
    
    def add_contract(self, contract_id: uuid.UUID):
        """Add a contract"""
        if contract_id not in self.contractIds:
            self.contractIds.append(contract_id)
    
    def add_assessment_run(self, assessment_run_id: uuid.UUID):
        """Add an assessment run"""
        if assessment_run_id not in self.assessmentRunIds:
            self.assessmentRunIds.append(assessment_run_id)
    
    def add_risk(self, risk_id: uuid.UUID):
        """Add a risk"""
        if risk_id not in self.riskIds:
            self.riskIds.append(risk_id)
    
    def add_control_implementation(self, implementation_id: uuid.UUID):
        """Add a control implementation"""
        if implementation_id not in self.controlImplementationIds:
            self.controlImplementationIds.append(implementation_id)
    
    def __str__(self):
        return f"{self.name} ({self.criticality})"

