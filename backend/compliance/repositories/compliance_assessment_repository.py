"""
Compliance Assessment Repository

Repository for managing ComplianceAssessment aggregates with support for
assessment lifecycle management, reporting, and cross-framework analytics.
"""

import uuid
from typing import List, Optional, Dict, Any
from django.db import models
from django.utils import timezone

from core.domain.repository import Repository
from ..models.compliance_assessment import ComplianceAssessment


class ComplianceAssessmentRepository(Repository[ComplianceAssessment]):
    """
    Repository for ComplianceAssessment aggregates.

    Provides methods for querying, managing, and analyzing compliance assessments
    across different frameworks and organizational scopes.
    """

    def __init__(self):
        super().__init__(ComplianceAssessment)

    def find_by_target(self, target_id: uuid.UUID, target_type: str) -> List[ComplianceAssessment]:
        """Find assessments for a specific target"""
        return list(self.model.objects.filter(
            target_id=target_id,
            target_type=target_type
        ).order_by('-created_at'))

    def find_by_framework(self, framework: str) -> List[ComplianceAssessment]:
        """Find assessments by framework"""
        return list(self.model.objects.filter(
            models.Q(primary_framework=framework) |
            models.Q(additional_frameworks__contains=[framework])
        ).order_by('-created_at'))

    def find_by_status(self, status: str) -> List[ComplianceAssessment]:
        """Find assessments by status"""
        return list(self.model.objects.filter(status=status).order_by('-created_at'))

    def find_overdue_assessments(self) -> List[ComplianceAssessment]:
        """Find assessments that are overdue"""
        today = timezone.now().date()
        return list(self.model.objects.filter(
            planned_completion_date__lt=today,
            status__in=['planned', 'in_progress', 'evidence_collection']
        ).order_by('planned_completion_date'))

    def get_assessment_statistics_for_target(self, target_id: uuid.UUID, target_type: str) -> Dict[str, Any]:
        """Get assessment statistics for a specific target"""
        assessments = self.find_by_target(target_id, target_type)

        stats = {
            'total_assessments': len(assessments),
            'completed_assessments': len([a for a in assessments if a.status == 'completed']),
            'in_progress_assessments': len([a for a in assessments if a.status == 'in_progress']),
            'overdue_assessments': len([a for a in assessments if a.is_overdue]),
            'high_priority_assessments': len([a for a in assessments if a.priority in ['critical', 'high']]),
            'average_compliance_score': 0.0,
            'frameworks_covered': set(),
            'status_distribution': {}
        }

        # Calculate averages and distributions
        completed_scores = [a.overall_compliance_score for a in assessments if a.status == 'completed' and a.overall_compliance_score > 0]
        if completed_scores:
            stats['average_compliance_score'] = round(sum(completed_scores) / len(completed_scores), 2)

        # Collect frameworks and status distribution
        for assessment in assessments:
            stats['frameworks_covered'].add(assessment.primary_framework)
            if assessment.additional_frameworks:
                stats['frameworks_covered'].update(assessment.additional_frameworks)

            stats['status_distribution'][assessment.status] = stats['status_distribution'].get(assessment.status, 0) + 1

        stats['frameworks_covered'] = list(stats['frameworks_covered'])
        return stats