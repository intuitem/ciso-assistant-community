"""
DataAsset Aggregate

Represents a data asset (collection of data).
"""

import uuid
from typing import List, Optional
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    DataAssetCreated,
    DataAssetActivated,
    DataAssetRetired,
)


class DataAsset(AggregateRoot):
    """
    Data Asset aggregate root.
    
    Represents a data asset with categories, personal data flags, and retention policies.
    """
    
    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        RETIRED = "retired", "Retired"
    
    # Basic fields
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    # Data characteristics
    data_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of data category strings"
    )
    contains_personal_data = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this asset contains personal data"
    )
    retention_policy = models.TextField(
        blank=True,
        null=True,
        help_text="Retention policy description"
    )
    
    # Lifecycle
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
        help_text="Array of asset IDs that store this data"
    )
    ownerOrgUnitIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of owner organizational unit IDs"
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "privacy_data_assets"
        verbose_name = "Data Asset"
        verbose_name_plural = "Data Assets"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["contains_personal_data"]),
            models.Index(fields=["name"]),
        ]
    
    def create(self, name: str, description: str = None,
               data_categories: List[str] = None,
               contains_personal_data: bool = False,
               retention_policy: str = None):
        """
        Create a new data asset.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.description = description
        self.data_categories = data_categories or []
        self.contains_personal_data = contains_personal_data
        self.retention_policy = retention_policy
        self.lifecycle_state = self.LifecycleState.DRAFT
        
        event = DataAssetCreated()
        event.payload = {
            "data_asset_id": str(self.id),
            "name": name,
            "contains_personal_data": contains_personal_data,
        }
        self._raise_event(event)
    
    def activate(self):
        """Activate the data asset"""
        if self.lifecycle_state != self.LifecycleState.ACTIVE:
            self.lifecycle_state = self.LifecycleState.ACTIVE
            
            event = DataAssetActivated()
            event.payload = {
                "data_asset_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def retire(self):
        """Retire the data asset"""
        if self.lifecycle_state != self.LifecycleState.RETIRED:
            self.lifecycle_state = self.LifecycleState.RETIRED
            
            event = DataAssetRetired()
            event.payload = {
                "data_asset_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def add_data_category(self, category: str):
        """Add a data category"""
        if category not in self.data_categories:
            self.data_categories.append(category)
    
    def add_asset(self, asset_id: uuid.UUID):
        """Add an asset that stores this data"""
        if asset_id not in self.assetIds:
            self.assetIds.append(asset_id)
    
    def assign_owner(self, org_unit_id: uuid.UUID):
        """Assign an owner organizational unit"""
        if org_unit_id not in self.ownerOrgUnitIds:
            self.ownerOrgUnitIds.append(org_unit_id)
    
    def __str__(self):
        return self.name

