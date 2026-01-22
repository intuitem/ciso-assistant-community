"""
ThirdPartyPosture Read Model

Denormalized read model for third party posture dashboards.
"""

from django.db import models
from core.domain.aggregate import Entity


class ThirdPartyPosture(Entity):
    """
    Read model for third party posture.
    
    Denormalized for fast dashboard queries without joins.
    Includes active contracts, latest assessments, findings, open risks, and exceptions.
    """
    
    # Third party reference
    third_party_id = models.UUIDField(unique=True, db_index=True)
    third_party_name = models.CharField(max_length=255, db_index=True)
    criticality = models.CharField(max_length=20, db_index=True)
    
    # Contracts summary
    active_contracts_count = models.IntegerField(default=0)
    expired_contracts_count = models.IntegerField(default=0)
    
    # Assessments summary
    total_assessments = models.IntegerField(default=0)
    latest_assessment_date = models.DateTimeField(null=True, blank=True)
    open_findings_count = models.IntegerField(default=0)
    
    # Risks summary
    open_risks_count = models.IntegerField(default=0)
    critical_risks_count = models.IntegerField(default=0)
    
    # Exceptions summary
    active_exceptions_count = models.IntegerField(default=0)
    
    # Last updated
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "third_party_management_third_party_postures"
        verbose_name = "Third Party Posture"
        verbose_name_plural = "Third Party Postures"
        indexes = [
            models.Index(fields=["third_party_id"]),
            models.Index(fields=["criticality"]),
        ]
    
    def __str__(self):
        return f"{self.third_party_name} Posture"

