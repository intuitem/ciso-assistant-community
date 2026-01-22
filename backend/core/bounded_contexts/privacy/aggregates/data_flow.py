"""
DataFlow Aggregate

Represents a data flow between systems.
"""

import uuid
from typing import List, Optional
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    DataFlowEstablished,
    DataFlowChanged,
    DataFlowActivated,
    DataFlowRetired,
)


class DataFlow(AggregateRoot):
    """
    Data Flow aggregate root.
    
    Represents a data flow between source and destination systems.
    """
    
    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        RETIRED = "retired", "Retired"
    
    # Basic fields
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    purpose = models.TextField(blank=True, null=True, help_text="Purpose of the data flow")
    
    # Source and destination
    source_system_asset_id = models.UUIDField(db_index=True, help_text="ID of the source system asset")
    destination_system_asset_id = models.UUIDField(db_index=True, help_text="ID of the destination system asset")
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.DRAFT,
        db_index=True
    )
    
    # Embedded ID arrays (replacing ManyToMany)
    dataAssetIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of data asset IDs flowing through this flow"
    )
    thirdPartyIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of third party IDs involved in this flow"
    )
    controlImplementationIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of control implementation IDs"
    )
    privacyRiskIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of privacy risk IDs"
    )
    
    # Transfer mechanisms and security
    transfer_mechanisms = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of transfer mechanism strings (e.g., API, SFTP, Email)"
    )
    encryption_in_transit = models.BooleanField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Whether data is encrypted in transit"
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "privacy_data_flows"
        verbose_name = "Data Flow"
        verbose_name_plural = "Data Flows"
        indexes = [
            models.Index(fields=["source_system_asset_id", "destination_system_asset_id"]),
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["name"]),
        ]
    
    def create(self, name: str, source_system_asset_id: uuid.UUID,
               destination_system_asset_id: uuid.UUID,
               description: str = None, purpose: str = None,
               transfer_mechanisms: List[str] = None,
               encryption_in_transit: Optional[bool] = None):
        """
        Create a new data flow.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.description = description
        self.purpose = purpose
        self.source_system_asset_id = source_system_asset_id
        self.destination_system_asset_id = destination_system_asset_id
        self.transfer_mechanisms = transfer_mechanisms or []
        self.encryption_in_transit = encryption_in_transit
        self.lifecycle_state = self.LifecycleState.DRAFT
        
        event = DataFlowEstablished()
        event.payload = {
            "data_flow_id": str(self.id),
            "name": name,
            "source_system_asset_id": str(source_system_asset_id),
            "destination_system_asset_id": str(destination_system_asset_id),
        }
        self._raise_event(event)
    
    def activate(self):
        """Activate the data flow"""
        if self.lifecycle_state != self.LifecycleState.ACTIVE:
            self.lifecycle_state = self.LifecycleState.ACTIVE
            
            event = DataFlowActivated()
            event.payload = {
                "data_flow_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def retire(self):
        """Retire the data flow"""
        if self.lifecycle_state != self.LifecycleState.RETIRED:
            self.lifecycle_state = self.LifecycleState.RETIRED
            
            event = DataFlowRetired()
            event.payload = {
                "data_flow_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def change(self, changes: dict):
        """
        Change the data flow.
        
        Args:
            changes: Dictionary of changes (e.g., {'purpose': 'New purpose', 'encryption_in_transit': True})
        """
        for key, value in changes.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        event = DataFlowChanged()
        event.payload = {
            "data_flow_id": str(self.id),
            "changes": changes,
        }
        self._raise_event(event)
    
    def add_data_asset(self, data_asset_id: uuid.UUID):
        """Add a data asset to this flow"""
        if data_asset_id not in self.dataAssetIds:
            self.dataAssetIds.append(data_asset_id)
    
    def add_third_party(self, third_party_id: uuid.UUID):
        """Add a third party to this flow"""
        if third_party_id not in self.thirdPartyIds:
            self.thirdPartyIds.append(third_party_id)
    
    def add_control_implementation(self, implementation_id: uuid.UUID):
        """Add a control implementation to this flow"""
        if implementation_id not in self.controlImplementationIds:
            self.controlImplementationIds.append(implementation_id)
    
    def add_privacy_risk(self, risk_id: uuid.UUID):
        """Add a privacy risk to this flow"""
        if risk_id not in self.privacyRiskIds:
            self.privacyRiskIds.append(risk_id)
    
    def add_transfer_mechanism(self, mechanism: str):
        """Add a transfer mechanism"""
        if mechanism not in self.transfer_mechanisms:
            self.transfer_mechanisms.append(mechanism)
    
    def __str__(self):
        return f"{self.name} ({self.source_system_asset_id} → {self.destination_system_asset_id})"

