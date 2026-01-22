"""
Repository for PolicyAcknowledgement associations
"""

from typing import Optional, List
from uuid import UUID
from django.utils import timezone
from core.domain.repository import Repository
from ..associations.policy_acknowledgement import PolicyAcknowledgement


class PolicyAcknowledgementRepository(Repository[PolicyAcknowledgement]):
    """Repository for PolicyAcknowledgement associations"""

    def __init__(self):
        super().__init__(PolicyAcknowledgement)

    def find_by_policy(self, policy_id: UUID) -> List[PolicyAcknowledgement]:
        """Find all acknowledgements for a policy"""
        return list(PolicyAcknowledgement.objects.filter(policyId=policy_id))

    def find_by_user(self, user_id: UUID) -> List[PolicyAcknowledgement]:
        """Find all acknowledgements by a user"""
        return list(PolicyAcknowledgement.objects.filter(userId=user_id))

    def find_by_policy_and_user(self, policy_id: UUID, user_id: UUID) -> Optional[PolicyAcknowledgement]:
        """Find acknowledgement for a specific policy and user combination"""
        return PolicyAcknowledgement.objects.filter(
            policyId=policy_id,
            userId=user_id
        ).first()

    def find_acknowledged(self) -> List[PolicyAcknowledgement]:
        """Find all completed acknowledgements"""
        return list(PolicyAcknowledgement.objects.filter(acknowledged_at__isnull=False))

    def find_pending(self) -> List[PolicyAcknowledgement]:
        """Find all pending acknowledgements"""
        return list(PolicyAcknowledgement.objects.filter(acknowledged_at__isnull=True))

    def find_by_method(self, method: str) -> List[PolicyAcknowledgement]:
        """Find acknowledgements by method (clickwrap, signature, etc.)"""
        return list(PolicyAcknowledgement.objects.filter(method=method))

    def find_recent(self, days: int = 30) -> List[PolicyAcknowledgement]:
        """Find acknowledgements from the last N days"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return list(PolicyAcknowledgement.objects.filter(
            acknowledged_at__gte=cutoff_date
        ))

    def count_by_policy(self, policy_id: UUID) -> dict:
        """Count acknowledgements for a policy (total, acknowledged, pending)"""
        total = PolicyAcknowledgement.objects.filter(policyId=policy_id).count()
        acknowledged = PolicyAcknowledgement.objects.filter(
            policyId=policy_id,
            acknowledged_at__isnull=False
        ).count()
        return {
            'total': total,
            'acknowledged': acknowledged,
            'pending': total - acknowledged
        }

    def has_user_acknowledged(self, policy_id: UUID, user_id: UUID) -> bool:
        """Check if a user has acknowledged a policy"""
        return PolicyAcknowledgement.objects.filter(
            policyId=policy_id,
            userId=user_id,
            acknowledged_at__isnull=False
        ).exists()
