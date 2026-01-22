"""
AssetOverview Read Model

Denormalized read model for asset dashboards.
Matches the DDD model specification for AssetOverview.
"""

from django.db import models
from core.domain.aggregate import Entity


class AssetOverview(Entity):
    """
    Read model for asset overview.
    
    Denormalized for fast dashboard queries without joins.
    Matches DDD model specification:
    - asset core fields
    - controlIds[] + latest ControlImplementation status summary
    - riskIds[] + residualScore summary
    - thirdPartyIds[] + contract/assessment status rollups
    """
    
    # Core fields (denormalized from Asset)
    asset_id = models.UUIDField(unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    ref_id = models.CharField(max_length=100, blank=True, null=True)
    asset_type = models.CharField(max_length=20, db_index=True)
    lifecycle_state = models.CharField(max_length=20, db_index=True)
    
    # Control summary (denormalized)
    control_count = models.IntegerField(default=0)
    control_implementation_status_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Summary of control implementation statuses"
    )
    
    # Risk summary (denormalized)
    risk_count = models.IntegerField(default=0)
    risk_residual_score_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Summary of risk residual scores"
    )
    
    # Third party summary (denormalized)
    third_party_count = models.IntegerField(default=0)
    third_party_contract_status_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Summary of third party contract statuses"
    )
    third_party_assessment_status_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Summary of third party assessment statuses"
    )
    
    # Service summary (denormalized)
    service_count = models.IntegerField(default=0)
    service_status_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Summary of service statuses"
    )
    
    # Last updated
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "asset_service_asset_overviews"
        verbose_name = "Asset Overview"
        verbose_name_plural = "Asset Overviews"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["asset_type"]),
            models.Index(fields=["name"]),
        ]
    
    def __str__(self):
        return f"{self.name} Overview"

