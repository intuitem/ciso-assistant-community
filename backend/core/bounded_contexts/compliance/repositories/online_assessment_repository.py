"""
Repository for OnlineAssessment aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.online_assessment import OnlineAssessment


class OnlineAssessmentRepository(Repository[OnlineAssessment]):
    """Repository for OnlineAssessment aggregates"""
    
    def __init__(self):
        super().__init__(OnlineAssessment)
    
    def find_by_name(self, name: str) -> Optional[OnlineAssessment]:
        """Find assessment by name"""
        return OnlineAssessment.objects.filter(name=name).first()
    
    def find_published(self) -> List[OnlineAssessment]:
        """Find all published assessments"""
        return list(
            OnlineAssessment.objects.filter(lifecycle_state=OnlineAssessment.LifecycleState.PUBLISHED)
        )
    
    def find_by_questionnaire(self, questionnaire_id: UUID) -> List[OnlineAssessment]:
        """Find all assessments for a questionnaire"""
        return list(OnlineAssessment.objects.filter(questionnaireId=questionnaire_id))

