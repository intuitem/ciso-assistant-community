"""
Consent Record Repository

Repository for managing ConsentRecord aggregates with support for
consent validation, withdrawal tracking, and compliance reporting.
"""

import uuid
from typing import List, Optional, Dict, Any
from django.db import models
from django.utils import timezone

from core.domain.repository import Repository
from ..models.consent_record import ConsentRecord


class ConsentRecordRepository(Repository[ConsentRecord]):
    """
    Repository for ConsentRecord aggregates.

    Provides methods for querying consent records by validity,
    withdrawal status, and compliance requirements.
    """

    def __init__(self):
        super().__init__(ConsentRecord)

    def find_by_data_subject(self, data_subject_id: str) -> List[ConsentRecord]:
        """Find all consent records for a data subject"""
        return list(self.model.objects.filter(data_subject_id=data_subject_id))

    def find_active_consents(self, data_subject_id: Optional[str] = None) -> List[ConsentRecord]:
        """Find active (valid) consent records"""
        query = self.model.objects.filter(status='active')
        if data_subject_id:
            query = query.filter(data_subject_id=data_subject_id)
        return list(query)

    def find_expired_consents(self) -> List[ConsentRecord]:
        """Find expired consent records"""
        today = timezone.now()
        return list(self.model.objects.filter(
            status='active',
            valid_until__lt=today
        ))

    def find_withdrawn_consents(self, data_subject_id: Optional[str] = None) -> List[ConsentRecord]:
        """Find withdrawn consent records"""
        query = self.model.objects.filter(withdrawn=True)
        if data_subject_id:
            query = query.filter(data_subject_id=data_subject_id)
        return list(query)

    def find_due_for_renewal(self, days_ahead: int = 30) -> List[ConsentRecord]:
        """Find consents due for renewal"""
        renewal_date = timezone.now() + timezone.timedelta(days=days_ahead)
        return list(self.model.objects.filter(
            status='active',
            valid_until__lte=renewal_date,
            auto_renewal=False
        ))

    def get_consent_statistics(self) -> Dict[str, Any]:
        """Get comprehensive consent statistics"""
        consents = list(self.model.objects.all())

        stats = {
            'total_consents': len(consents),
            'active_consents': len([c for c in consents if c.is_valid]),
            'expired_consents': len([c for c in consents if c.is_expired]),
            'withdrawn_consents': len([c for c in consents if c.withdrawn]),
            'pending_verification': len([c for c in consents if c.status == 'pending_verification']),
            'consent_withdrawal_rate': 0.0,
            'average_consent_duration_days': 0,
            'consent_method_distribution': {},
            'legal_basis_distribution': {},
            'generated_at': str(timezone.now())
        }

        # Calculate withdrawal rate
        if stats['total_consents'] > 0:
            stats['consent_withdrawal_rate'] = round(
                (stats['withdrawn_consents'] / stats['total_consents']) * 100, 2
            )

        # Calculate average duration
        durations = [c.consent_duration_days for c in consents if c.consent_duration_days]
        if durations:
            stats['average_consent_duration_days'] = round(sum(durations) / len(durations), 1)

        # Calculate distributions
        for consent in consents:
            stats['consent_method_distribution'][consent.consent_method] = \
                stats['consent_method_distribution'].get(consent.consent_method, 0) + 1
            stats['legal_basis_distribution'][consent.legal_basis] = \
                stats['legal_basis_distribution'].get(consent.legal_basis, 0) + 1

        return stats

    def bulk_expire_consents(self, consent_ids: List[str]) -> int:
        """Bulk expire multiple consents"""
        consents = self.model.objects.filter(id__in=consent_ids)
        expired_count = 0

        for consent in consents:
            if consent.status == 'active':
                consent.status = 'expired'
                consent.save()
                expired_count += 1

        return expired_count

    def find_consents_by_purpose(self, purpose: str) -> List[ConsentRecord]:
        """Find consents that include a specific processing purpose"""
        return list(self.model.objects.filter(processing_purposes__contains=[purpose]))

    def find_consents_by_legal_basis(self, legal_basis: str) -> List[ConsentRecord]:
        """Find consents by legal basis"""
        return list(self.model.objects.filter(legal_basis=legal_basis))
