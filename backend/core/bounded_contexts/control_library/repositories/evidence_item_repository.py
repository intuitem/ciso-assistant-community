"""
Repository for EvidenceItem aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.evidence_item import EvidenceItem


class EvidenceItemRepository(Repository[EvidenceItem]):
    """Repository for EvidenceItem aggregates"""
    
    def __init__(self):
        super().__init__(EvidenceItem)
    
    def find_by_name(self, name: str) -> Optional[EvidenceItem]:
        """Find evidence item by name"""
        return EvidenceItem.objects.filter(name=name).first()
    
    def find_verified(self) -> List[EvidenceItem]:
        """Find all verified evidence items"""
        return list(
            EvidenceItem.objects.filter(lifecycle_state=EvidenceItem.LifecycleState.VERIFIED)
        )
    
    def find_by_source_type(self, source_type: str) -> List[EvidenceItem]:
        """Find evidence items by source type"""
        return list(EvidenceItem.objects.filter(source_type=source_type))
    
    def find_expired(self) -> List[EvidenceItem]:
        """Find all expired evidence items"""
        from django.utils import timezone
        return list(
            EvidenceItem.objects.filter(
                expires_at__lt=timezone.now(),
                lifecycle_state__ne=EvidenceItem.LifecycleState.EXPIRED
            )
        )

