"""
AssetLabel Supporting Entity

Represents a label/tag for assets.
"""

import uuid
from django.db import models
from core.domain.aggregate import Entity


class AssetLabel(Entity):
    """
    Asset label supporting entity.
    
    Used for categorizing and filtering assets.
    """
    
    name = models.CharField(max_length=255, unique=True, db_index=True)
    color = models.CharField(max_length=7, blank=True, null=True, help_text="Hex color code")
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = "asset_service_asset_labels"
        verbose_name = "Asset Label"
        verbose_name_plural = "Asset Labels"
        indexes = [
            models.Index(fields=["name"]),
        ]
    
    def __str__(self):
        return self.name

