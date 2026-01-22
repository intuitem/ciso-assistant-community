"""
ChecklistScore Aggregate

Represents scoring/statistics for a STIG checklist.
"""

import uuid
from typing import Optional
from django.db import models
from django.utils import timezone

from core.domain.aggregate import AggregateRoot


class ChecklistScore(AggregateRoot):
    """
    Checklist Score aggregate.

    Stores calculated statistics for a STIG checklist, including counts
    by severity category and status. Updated by projection handlers.
    """

    # Identity
    checklistId = models.UUIDField(
        unique=True,
        db_index=True,
        help_text="ID of the STIG checklist"
    )
    systemGroupId = models.UUIDField(
        db_index=True,
        null=True,
        blank=True,
        help_text="ID of the system group (for system-level aggregation)"
    )

    # Host information (denormalized for queries)
    hostName = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Hostname from checklist"
    )
    stigType = models.CharField(
        max_length=255,
        db_index=True,
        help_text="STIG type"
    )

    # Category 1 (High/CAT I) counts
    totalCat1Open = models.IntegerField(
        default=0,
        help_text="Total CAT I open vulnerabilities"
    )
    totalCat1NotAFinding = models.IntegerField(
        default=0,
        help_text="Total CAT I not a finding vulnerabilities"
    )
    totalCat1NotApplicable = models.IntegerField(
        default=0,
        help_text="Total CAT I not applicable vulnerabilities"
    )
    totalCat1NotReviewed = models.IntegerField(
        default=0,
        help_text="Total CAT I not reviewed vulnerabilities"
    )

    # Category 2 (Medium/CAT II) counts
    totalCat2Open = models.IntegerField(
        default=0,
        help_text="Total CAT II open vulnerabilities"
    )
    totalCat2NotAFinding = models.IntegerField(
        default=0,
        help_text="Total CAT II not a finding vulnerabilities"
    )
    totalCat2NotApplicable = models.IntegerField(
        default=0,
        help_text="Total CAT II not applicable vulnerabilities"
    )
    totalCat2NotReviewed = models.IntegerField(
        default=0,
        help_text="Total CAT II not reviewed vulnerabilities"
    )

    # Category 3 (Low/CAT III) counts
    totalCat3Open = models.IntegerField(
        default=0,
        help_text="Total CAT III open vulnerabilities"
    )
    totalCat3NotAFinding = models.IntegerField(
        default=0,
        help_text="Total CAT III not a finding vulnerabilities"
    )
    totalCat3NotApplicable = models.IntegerField(
        default=0,
        help_text="Total CAT III not applicable vulnerabilities"
    )
    totalCat3NotReviewed = models.IntegerField(
        default=0,
        help_text="Total CAT III not reviewed vulnerabilities"
    )

    # Metadata
    lastCalculatedAt = models.DateTimeField(
        db_index=True,
        help_text="When the score was last calculated"
    )

    class Meta:
        db_table = 'rmf_checklist_scores'
        verbose_name = 'Checklist Score'
        verbose_name_plural = 'Checklist Scores'
        ordering = ['-lastCalculatedAt']
        indexes = [
            models.Index(fields=['checklistId']),
            models.Index(fields=['systemGroupId']),
            models.Index(fields=['stigType']),
            models.Index(fields=['lastCalculatedAt']),
        ]

    def __str__(self):
        return f"ChecklistScore({self.id}): {self.hostName} - {self.stigType}"

    def save(self, *args, **kwargs):
        """Override save to set last calculated timestamp"""
        self.lastCalculatedAt = timezone.now()
        super().save(*args, **kwargs)

    # Computed property accessors
    @property
    def totalOpen(self) -> int:
        """Total open vulnerabilities across all categories"""
        return self.totalCat1Open + self.totalCat2Open + self.totalCat3Open

    @property
    def totalNotAFinding(self) -> int:
        """Total not a finding vulnerabilities across all categories"""
        return (self.totalCat1NotAFinding + self.totalCat2NotAFinding + self.totalCat3NotAFinding)

    @property
    def totalNotApplicable(self) -> int:
        """Total not applicable vulnerabilities across all categories"""
        return (self.totalCat1NotApplicable + self.totalCat2NotApplicable + self.totalCat3NotApplicable)

    @property
    def totalNotReviewed(self) -> int:
        """Total not reviewed vulnerabilities across all categories"""
        return (self.totalCat1NotReviewed + self.totalCat2NotReviewed + self.totalCat3NotReviewed)

    @property
    def totalCat1(self) -> int:
        """Total CAT I vulnerabilities (all statuses)"""
        return (self.totalCat1Open + self.totalCat1NotAFinding +
                self.totalCat1NotApplicable + self.totalCat1NotReviewed)

    @property
    def totalCat2(self) -> int:
        """Total CAT II vulnerabilities (all statuses)"""
        return (self.totalCat2Open + self.totalCat2NotAFinding +
                self.totalCat2NotApplicable + self.totalCat2NotReviewed)

    @property
    def totalCat3(self) -> int:
        """Total CAT III vulnerabilities (all statuses)"""
        return (self.totalCat3Open + self.totalCat3NotAFinding +
                self.totalCat3NotApplicable + self.totalCat3NotReviewed)

    @property
    def totalVulnerabilities(self) -> int:
        """Total vulnerabilities across all categories and statuses"""
        return self.totalCat1 + self.totalCat2 + self.totalCat3

    # Business methods
    def create_score(self, checklist_id: uuid.UUID, system_group_id: Optional[uuid.UUID],
                    host_name: str, stig_type: str) -> None:
        """Create a new checklist score record"""
        self.checklistId = checklist_id
        self.systemGroupId = system_group_id
        self.hostName = host_name
        self.stigType = stig_type

        # Initialize all counts to 0
        self.reset_counts()

        from ..domain_events import ChecklistScoreCalculated
        self._raise_event(ChecklistScoreCalculated(
            aggregate_id=self.id,
            checklist_id=str(checklist_id),
            total_open=self.totalOpen,
            total_vulnerabilities=self.totalVulnerabilities
        ))

    def reset_counts(self) -> None:
        """Reset all counts to zero"""
        self.totalCat1Open = 0
        self.totalCat1NotAFinding = 0
        self.totalCat1NotApplicable = 0
        self.totalCat1NotReviewed = 0

        self.totalCat2Open = 0
        self.totalCat2NotAFinding = 0
        self.totalCat2NotApplicable = 0
        self.totalCat2NotReviewed = 0

        self.totalCat3Open = 0
        self.totalCat3NotAFinding = 0
        self.totalCat3NotApplicable = 0
        self.totalCat3NotReviewed = 0

    def update_from_findings(self, findings_data: dict) -> None:
        """
        Update counts from vulnerability findings data.

        Args:
            findings_data: Dict with structure:
                {
                    'cat1': {'open': count, 'not_a_finding': count, ...},
                    'cat2': {...},
                    'cat3': {...}
                }
        """
        self.reset_counts()

        # Update CAT 1 counts
        cat1_data = findings_data.get('cat1', {})
        self.totalCat1Open = cat1_data.get('open', 0)
        self.totalCat1NotAFinding = cat1_data.get('not_a_finding', 0)
        self.totalCat1NotApplicable = cat1_data.get('not_applicable', 0)
        self.totalCat1NotReviewed = cat1_data.get('not_reviewed', 0)

        # Update CAT 2 counts
        cat2_data = findings_data.get('cat2', {})
        self.totalCat2Open = cat2_data.get('open', 0)
        self.totalCat2NotAFinding = cat2_data.get('not_a_finding', 0)
        self.totalCat2NotApplicable = cat2_data.get('not_applicable', 0)
        self.totalCat2NotReviewed = cat2_data.get('not_reviewed', 0)

        # Update CAT 3 counts
        cat3_data = findings_data.get('cat3', {})
        self.totalCat3Open = cat3_data.get('open', 0)
        self.totalCat3NotAFinding = cat3_data.get('not_a_finding', 0)
        self.totalCat3NotApplicable = cat3_data.get('not_applicable', 0)
        self.totalCat3NotReviewed = cat3_data.get('not_reviewed', 0)

        from ..domain_events import ChecklistScoreUpdated
        self._raise_event(ChecklistScoreUpdated(
            aggregate_id=self.id,
            checklist_id=str(self.checklistId),
            total_open=self.totalOpen,
            total_vulnerabilities=self.totalVulnerabilities
        ))

    def update_system_assignment(self, system_group_id: Optional[uuid.UUID]) -> None:
        """Update the system group assignment"""
        self.systemGroupId = system_group_id

    # Query methods
    def get_score_summary(self) -> dict:
        """Get a summary of the current scores"""
        return {
            'total_open': self.totalOpen,
            'total_not_a_finding': self.totalNotAFinding,
            'total_not_applicable': self.totalNotApplicable,
            'total_not_reviewed': self.totalNotReviewed,
            'total_vulnerabilities': self.totalVulnerabilities,
            'categories': {
                'cat1': {
                    'total': self.totalCat1,
                    'open': self.totalCat1Open,
                    'not_a_finding': self.totalCat1NotAFinding,
                    'not_applicable': self.totalCat1NotApplicable,
                    'not_reviewed': self.totalCat1NotReviewed
                },
                'cat2': {
                    'total': self.totalCat2,
                    'open': self.totalCat2Open,
                    'not_a_finding': self.totalCat2NotAFinding,
                    'not_applicable': self.totalCat2NotApplicable,
                    'not_reviewed': self.totalCat2NotReviewed
                },
                'cat3': {
                    'total': self.totalCat3,
                    'open': self.totalCat3Open,
                    'not_a_finding': self.totalCat3NotAFinding,
                    'not_applicable': self.totalCat3NotApplicable,
                    'not_reviewed': self.totalCat3NotReviewed
                }
            }
        }

    def get_compliance_percentage(self) -> float:
        """Get compliance percentage (closed vulnerabilities / total)"""
        if self.totalVulnerabilities == 0:
            return 100.0
        closed_count = (self.totalNotAFinding + self.totalNotApplicable)
        return round((closed_count / self.totalVulnerabilities) * 100, 1)

    def is_compliant(self, threshold: float = 80.0) -> bool:
        """Check if checklist meets compliance threshold"""
        return self.get_compliance_percentage() >= threshold

    def get_high_priority_open_count(self) -> int:
        """Get count of high priority (CAT I) open vulnerabilities"""
        return self.totalCat1Open

    def has_critical_findings(self) -> bool:
        """Check if there are any CAT I open vulnerabilities"""
        return self.totalCat1Open > 0
