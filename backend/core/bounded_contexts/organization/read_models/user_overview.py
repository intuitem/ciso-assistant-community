"""
UserOverview Read Model

Denormalized read model for user dashboards.
"""

from django.db import models
from core.domain.aggregate import Entity


class UserOverview(Entity):
    """
    Read model for user overview.
    
    Denormalized for fast dashboard queries without joins.
    """
    
    # Core fields (denormalized from User)
    user_id = models.UUIDField(unique=True, db_index=True)
    email = models.EmailField(db_index=True)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    lifecycle_state = models.CharField(max_length=20, db_index=True)
    
    # Aggregated counts
    group_count = models.IntegerField(default=0)
    org_unit_count = models.IntegerField(default=0)
    responsibility_count = models.IntegerField(default=0)
    
    # Group names (denormalized for display)
    group_names = models.JSONField(default=list, blank=True)
    
    # Org unit names (denormalized for display)
    org_unit_names = models.JSONField(default=list, blank=True)
    
    # Last updated
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "organization_user_overviews"
        verbose_name = "User Overview"
        verbose_name_plural = "User Overviews"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["lifecycle_state"]),
        ]
    
    def __str__(self):
        return f"{self.display_name or self.email} Overview"

