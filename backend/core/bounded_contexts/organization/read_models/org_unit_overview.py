"""
OrgUnitOverview Read Model

Denormalized read model for organizational unit dashboards.
"""

from django.db import models
from core.domain.aggregate import Entity


class OrgUnitOverview(Entity):
    """
    Read model for organizational unit overview.
    
    Denormalized for fast dashboard queries without joins.
    """
    
    # Core fields (denormalized from OrgUnit)
    org_unit_id = models.UUIDField(unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    ref_id = models.CharField(max_length=100, blank=True, null=True)
    lifecycle_state = models.CharField(max_length=20, db_index=True)
    
    # Aggregated counts
    child_count = models.IntegerField(default=0)
    owner_count = models.IntegerField(default=0)
    user_count = models.IntegerField(default=0)
    
    # Last updated
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "organization_org_unit_overviews"
        verbose_name = "Org Unit Overview"
        verbose_name_plural = "Org Unit Overviews"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["name"]),
        ]
    
    def __str__(self):
        return f"{self.name} Overview"

