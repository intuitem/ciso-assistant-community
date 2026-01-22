"""
Service Aggregate

Represents a service in the organization.
"""

import uuid
from typing import Optional
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    ServiceCreated,
    ServiceOperational,
    ServiceRetired,
)


class Service(AggregateRoot):
    """
    Service aggregate root.
    
    Represents a service with embedded ID arrays for relationships.
    """
    
    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPERATIONAL = "operational", "Operational"
        RETIRED = "retired", "Retired"
    
    # Basic fields
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    ref_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    
    # Classification and lifecycle
    serviceClassificationId = models.UUIDField(null=True, blank=True, db_index=True)
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.DRAFT,
        db_index=True
    )
    
    # Embedded ID arrays (replacing ManyToMany)
    assetIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of asset IDs"
    )
    thirdPartyIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of third party IDs"
    )
    controlIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of control IDs"
    )
    riskIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of risk IDs"
    )
    contractIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of service contract IDs"
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "asset_service_services"
        verbose_name = "Service"
        verbose_name_plural = "Services"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["name"]),
            models.Index(fields=["ref_id"]),
        ]
    
    def create(self, name: str, description: str = None, ref_id: str = None,
               service_classification_id: Optional[uuid.UUID] = None):
        """
        Create a new service.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.description = description
        self.ref_id = ref_id
        self.serviceClassificationId = service_classification_id
        self.lifecycle_state = self.LifecycleState.DRAFT
        
        event = ServiceCreated()
        event.payload = {
            "name": name,
            "ref_id": ref_id,
        }
        self._raise_event(event)
    
    def make_operational(self):
        """Make the service operational"""
        if self.lifecycle_state != self.LifecycleState.OPERATIONAL:
            self.lifecycle_state = self.LifecycleState.OPERATIONAL
            
            event = ServiceOperational()
            event.payload = {
                "service_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def retire(self):
        """Retire the service"""
        if self.lifecycle_state != self.LifecycleState.RETIRED:
            self.lifecycle_state = self.LifecycleState.RETIRED
            
            event = ServiceRetired()
            event.payload = {
                "service_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def link_asset(self, asset_id: uuid.UUID):
        """Link an asset to this service"""
        if asset_id not in self.assetIds:
            self.assetIds.append(asset_id)
    
    def link_third_party(self, third_party_id: uuid.UUID):
        """Link a third party to this service"""
        if third_party_id not in self.thirdPartyIds:
            self.thirdPartyIds.append(third_party_id)
    
    def assign_control(self, control_id: uuid.UUID):
        """Assign a control to this service"""
        if control_id not in self.controlIds:
            self.controlIds.append(control_id)
    
    def assign_risk(self, risk_id: uuid.UUID):
        """Assign a risk to this service"""
        if risk_id not in self.riskIds:
            self.riskIds.append(risk_id)
    
    def add_contract(self, contract_id: uuid.UUID):
        """Add a service contract to this service"""
        if contract_id not in self.contractIds:
            self.contractIds.append(contract_id)
    
    def __str__(self):
        return f"{self.name} ({self.ref_id})" if self.ref_id else self.name

