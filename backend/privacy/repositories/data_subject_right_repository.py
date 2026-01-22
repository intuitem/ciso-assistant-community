"""
Data Subject Right Repository

Repository for managing DataSubjectRight aggregates with support for
GDPR compliance tracking and rights request processing.
"""

import uuid
from typing import List, Optional, Dict, Any
from django.db import models
from django.utils import timezone

from core.domain.repository import Repository
from ..models.data_subject_right import DataSubjectRight


class DataSubjectRightRepository(Repository[DataSubjectRight]):
    """
    Repository for DataSubjectRight aggregates.

    Provides methods for querying and managing GDPR data subject rights requests.
    """

    def __init__(self):
        super().__init__(DataSubjectRight)

    def find_by_data_subject(self, data_subject_id: str) -> List[DataSubjectRight]:
        """Find all rights requests for a data subject"""
        return list(self.model.objects.filter(data_subject_id=data_subject_id))

    def find_overdue_requests(self) -> List[DataSubjectRight]:
        """Find requests that are overdue for completion"""
        today = timezone.now().date()
        return list(self.model.objects.filter(
            status__in=['received', 'processing', 'information_requested'],
            due_date__lt=today
        ))

    def find_pending_requests(self) -> List[DataSubjectRight]:
        """Find requests that are still pending"""
        return list(self.model.objects.filter(
            status__in=['received', 'processing', 'information_requested', 'verification_pending']
        ))

    def find_by_right_type(self, right_type: str) -> List[DataSubjectRight]:
        """Find requests by specific right type"""
        return list(self.model.objects.filter(primary_right=right_type))

    def get_dsr_statistics(self) -> Dict[str, Any]:
        """Get comprehensive DSR statistics"""
        requests = list(self.model.objects.all())

        stats = {
            'total_requests': len(requests),
            'completed_requests': len([r for r in requests if r.status == 'completed']),
            'pending_requests': len([r for r in requests if r.status in ['received', 'processing']]),
            'rejected_requests': len([r for r in requests if r.status == 'rejected']),
            'overdue_requests': len([r for r in requests if r.is_overdue]),
            'appeal_requests': len([r for r in requests if r.appeal_requested]),
            'average_processing_days': 0,
            'compliance_rate': 0.0,
            'right_type_distribution': {},
            'status_distribution': {},
            'generated_at': str(timezone.now())
        }

        # Calculate average processing time
        processing_times = [r.processing_duration_days for r in requests if r.processing_duration_days]
        if processing_times:
            stats['average_processing_days'] = round(sum(processing_times) / len(processing_times), 1)

        # Calculate compliance rate (completed within 30 days)
        timely_completed = len([r for r in requests if r.status == 'completed' and not r.is_overdue])
        if stats['completed_requests'] > 0:
            stats['compliance_rate'] = round((timely_completed / stats['completed_requests']) * 100, 2)

        # Calculate distributions
        for request in requests:
            stats['right_type_distribution'][request.primary_right] = \
                stats['right_type_distribution'].get(request.primary_right, 0) + 1
            stats['status_distribution'][request.status] = \
                stats['status_distribution'].get(request.status, 0) + 1

        return stats
