"""
CompliancePostureByFramework Read Model

Denormalized read model for compliance posture dashboards.
"""

from django.db import models
from core.domain.aggregate import Entity


class CompliancePostureByFramework(Entity):
    """
    Read model for compliance posture by framework.
    
    Denormalized for fast dashboard queries without joins.
    Includes requirement coverage, findings, exceptions, and audit history.
    """
    
    # Framework reference
    framework_id = models.UUIDField(unique=True, db_index=True)
    framework_name = models.CharField(max_length=255, db_index=True)
    framework_version = models.CharField(max_length=100, blank=True, null=True)
    
    # Requirement coverage
    total_requirements = models.IntegerField(default=0)
    active_requirements = models.IntegerField(default=0)
    requirements_with_controls = models.IntegerField(default=0)
    coverage_percentage = models.FloatField(default=0.0, help_text="Percentage of requirements with controls")
    
    # Findings summary
    open_findings_count = models.IntegerField(default=0)
    triaged_findings_count = models.IntegerField(default=0)
    remediating_findings_count = models.IntegerField(default=0)
    verified_findings_count = models.IntegerField(default=0)
    closed_findings_count = models.IntegerField(default=0)
    
    # Exceptions summary
    active_exceptions_count = models.IntegerField(default=0)
    expired_exceptions_count = models.IntegerField(default=0)
    
    # Audit history
    total_audits = models.IntegerField(default=0)
    recent_audit_date = models.DateField(null=True, blank=True)
    
    # Last updated
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "compliance_compliance_posture_by_framework"
        verbose_name = "Compliance Posture By Framework"
        verbose_name_plural = "Compliance Posture By Framework"
        indexes = [
            models.Index(fields=["framework_id"]),
            models.Index(fields=["framework_name"]),
        ]
    
    def __str__(self):
        return f"{self.framework_name} Posture"

