"""
AssetClassification Supporting Entity

Represents a classification for assets with CIA impact scores.
"""

import uuid
from django.db import models
from core.domain.aggregate import Entity


class AssetClassification(Entity):
    """
    Asset classification supporting entity.
    
    Contains CIA (Confidentiality, Integrity, Availability) impact scores.
    """
    
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    # CIA Impact scores (1-5 scale)
    confidentiality_impact = models.IntegerField(default=1, help_text="Confidentiality impact (1-5)")
    integrity_impact = models.IntegerField(default=1, help_text="Integrity impact (1-5)")
    availability_impact = models.IntegerField(default=1, help_text="Availability impact (1-5)")
    
    class Meta:
        db_table = "asset_service_asset_classifications"
        verbose_name = "Asset Classification"
        verbose_name_plural = "Asset Classifications"
        indexes = [
            models.Index(fields=["name"]),
        ]
    
    def get_cia_score(self) -> int:
        """Calculate total CIA score"""
        return self.confidentiality_impact + self.integrity_impact + self.availability_impact
    
    def __str__(self):
        return f"{self.name} (C:{self.confidentiality_impact}, I:{self.integrity_impact}, A:{self.availability_impact})"

