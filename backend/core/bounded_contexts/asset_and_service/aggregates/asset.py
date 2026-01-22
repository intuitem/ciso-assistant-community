"""
Asset Aggregate

Represents an asset in the organization.
"""

import uuid
from typing import Optional, List
from django.db import models
from django.core.exceptions import ValidationError

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    AssetCreated,
    AssetActivated,
    AssetArchived,
    ControlAssignedToAsset,
    RiskAssignedToAsset,
    ServiceLinkedToAsset,
)


class Asset(AggregateRoot):
    """
    Asset aggregate root.
    
    Represents an asset with embedded ID arrays for relationships.
    """
    
    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_USE = "in_use", "In Use"
        ARCHIVED = "archived", "Archived"
    
    class AssetType(models.TextChoices):
        PRIMARY = "primary", "Primary"
        SUPPORT = "support", "Support"
    
    # Basic fields
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    ref_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    
    # Type and lifecycle
    asset_type = models.CharField(
        max_length=20,
        choices=AssetType.choices,
        default=AssetType.SUPPORT,
        db_index=True
    )
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.DRAFT,
        db_index=True
    )
    
    # Classification
    assetClassificationId = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Embedded ID arrays (replacing ManyToMany)
    assetLabelIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of asset label IDs"
    )
    businessOwnerOrgUnitIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of business owner organizational unit IDs"
    )
    systemOwnerUserIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of system owner user IDs"
    )
    processIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of process IDs"
    )
    dataAssetIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of data asset IDs"
    )
    serviceIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of service IDs"
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
    
    # Additional fields
    business_value = models.CharField(max_length=200, blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "asset_service_assets"
        verbose_name = "Asset"
        verbose_name_plural = "Assets"
        indexes = [
            models.Index(fields=["lifecycle_state", "asset_type"]),
            models.Index(fields=["name"]),
            models.Index(fields=["ref_id"]),
        ]
    
    def create(self, name: str, description: str = None, ref_id: str = None, 
               asset_type: str = None, asset_classification_id: Optional[uuid.UUID] = None):
        """
        Create a new asset.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.description = description
        self.ref_id = ref_id
        self.asset_type = asset_type or self.AssetType.SUPPORT
        self.assetClassificationId = asset_classification_id
        self.lifecycle_state = self.LifecycleState.DRAFT
        
        event = AssetCreated()
        event.payload = {
            "name": name,
            "ref_id": ref_id,
            "asset_type": self.asset_type,
        }
        self._raise_event(event)
    
    def activate(self):
        """Activate the asset (move to InUse state)"""
        if self.lifecycle_state != self.LifecycleState.IN_USE:
            self.lifecycle_state = self.LifecycleState.IN_USE
            
            event = AssetActivated()
            event.payload = {
                "asset_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def archive(self):
        """Archive the asset"""
        if self.lifecycle_state != self.LifecycleState.ARCHIVED:
            self.lifecycle_state = self.LifecycleState.ARCHIVED
            
            event = AssetArchived()
            event.payload = {
                "asset_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def assign_control(self, control_id: uuid.UUID):
        """Assign a control to this asset"""
        if control_id not in self.controlIds:
            self.controlIds.append(control_id)
            
            event = ControlAssignedToAsset()
            event.payload = {
                "asset_id": str(self.id),
                "control_id": str(control_id),
            }
            self._raise_event(event)
    
    def assign_risk(self, risk_id: uuid.UUID):
        """Assign a risk to this asset"""
        if risk_id not in self.riskIds:
            self.riskIds.append(risk_id)
            
            event = RiskAssignedToAsset()
            event.payload = {
                "asset_id": str(self.id),
                "risk_id": str(risk_id),
            }
            self._raise_event(event)
    
    def link_service(self, service_id: uuid.UUID):
        """Link a service to this asset"""
        if service_id not in self.serviceIds:
            self.serviceIds.append(service_id)
            
            event = ServiceLinkedToAsset()
            event.payload = {
                "asset_id": str(self.id),
                "service_id": str(service_id),
            }
            self._raise_event(event)
    
    def assign_business_owner(self, org_unit_id: uuid.UUID):
        """Assign a business owner (org unit) to this asset"""
        if org_unit_id not in self.businessOwnerOrgUnitIds:
            self.businessOwnerOrgUnitIds.append(org_unit_id)
    
    def assign_system_owner(self, user_id: uuid.UUID):
        """Assign a system owner (user) to this asset"""
        if user_id not in self.systemOwnerUserIds:
            self.systemOwnerUserIds.append(user_id)
    
    def __str__(self):
        return f"{self.name} ({self.ref_id})" if self.ref_id else self.name

