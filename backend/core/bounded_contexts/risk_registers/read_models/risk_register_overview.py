"""
RiskRegisterOverview Read Model

Denormalized read model for risk register dashboards.
"""

from django.db import models
from core.domain.aggregate import Entity


class RiskRegisterOverview(Entity):
    """
    Read model for risk register overview.
    
    Denormalized for fast dashboard queries without joins.
    Includes risk counts by type and state.
    """
    
    class RiskType(models.TextChoices):
        ASSET = "asset", "Asset"
        THIRD_PARTY = "third_party", "Third Party"
        BUSINESS = "business", "Business"
    
    # Type and summary
    risk_type = models.CharField(max_length=20, choices=RiskType.choices, db_index=True)
    
    # Counts by state
    draft_count = models.IntegerField(default=0)
    assessed_count = models.IntegerField(default=0)
    treated_count = models.IntegerField(default=0)
    accepted_count = models.IntegerField(default=0)
    closed_count = models.IntegerField(default=0)
    
    # Scoring summary
    average_inherent_score = models.FloatField(null=True, blank=True)
    average_residual_score = models.FloatField(null=True, blank=True)
    
    # Last updated
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "risk_registers_risk_register_overviews"
        verbose_name = "Risk Register Overview"
        verbose_name_plural = "Risk Register Overviews"
        unique_together = [["risk_type"]]
        indexes = [
            models.Index(fields=["risk_type"]),
        ]
    
    def __str__(self):
        return f"{self.get_risk_type_display()} Risk Register Overview"

