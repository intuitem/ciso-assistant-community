"""
ServiceClassification Supporting Entity

Represents a classification for services.
"""

import uuid
from django.db import models
from core.domain.aggregate import Entity


class ServiceClassification(Entity):
    """
    Service classification supporting entity.
    
    Used for categorizing services.
    """
    
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = "asset_service_service_classifications"
        verbose_name = "Service Classification"
        verbose_name_plural = "Service Classifications"
        indexes = [
            models.Index(fields=["name"]),
        ]
    
    def __str__(self):
        return self.name

