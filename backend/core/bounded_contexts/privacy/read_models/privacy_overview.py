"""
PrivacyOverview Read Model

Denormalized read model for privacy dashboards.
"""

from django.db import models
from core.domain.aggregate import Entity


class PrivacyOverview(Entity):
    """
    Read model for privacy overview.
    
    Denormalized for fast dashboard queries without joins.
    Includes data asset count, data flow count, and privacy risks.
    """
    
    # Data asset summary
    total_data_assets = models.IntegerField(default=0)
    active_data_assets = models.IntegerField(default=0)
    data_assets_with_personal_data = models.IntegerField(default=0)
    
    # Data flow summary
    total_data_flows = models.IntegerField(default=0)
    active_data_flows = models.IntegerField(default=0)
    flows_without_encryption = models.IntegerField(default=0)
    
    # Privacy risks summary
    total_privacy_risks = models.IntegerField(default=0)
    open_privacy_risks = models.IntegerField(default=0)
    
    # Last updated
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "privacy_privacy_overviews"
        verbose_name = "Privacy Overview"
        verbose_name_plural = "Privacy Overviews"
    
    def __str__(self):
        return "Privacy Overview"

