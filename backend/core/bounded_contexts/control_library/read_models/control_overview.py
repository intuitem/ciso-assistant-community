"""
ControlOverview Read Model

Denormalized read model for control dashboards.
"""

from django.db import models
from core.domain.aggregate import Entity


class ControlOverview(Entity):
    """
    Read model for control overview.
    
    Denormalized for fast dashboard queries without joins.
    Includes implementation status summary.
    """
    
    # Core fields (denormalized from Control)
    control_id = models.UUIDField(unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    ref_id = models.CharField(max_length=100, blank=True, null=True)
    control_type = models.CharField(max_length=20, blank=True, null=True)
    lifecycle_state = models.CharField(max_length=20, db_index=True)
    
    # Implementation summary (denormalized)
    implementation_count = models.IntegerField(default=0)
    implementation_status_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Summary of implementation statuses by lifecycle state"
    )
    
    # Evidence summary (denormalized)
    evidence_count = models.IntegerField(default=0)
    
    # Related controls summary
    related_control_count = models.IntegerField(default=0)
    legal_requirement_count = models.IntegerField(default=0)
    
    # Last updated
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "control_library_control_overviews"
        verbose_name = "Control Overview"
        verbose_name_plural = "Control Overviews"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["control_type"]),
            models.Index(fields=["name"]),
        ]
    
    def __str__(self):
        return f"{self.name} Overview"

