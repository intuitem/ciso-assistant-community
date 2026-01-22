"""
OnlineAssessment Aggregate

Represents an online assessment (questionnaire-based).
"""

import uuid
from django.db import models

from core.domain.aggregate import AggregateRoot
from ..domain_events import (
    OnlineAssessmentCreated,
    OnlineAssessmentPublished,
    OnlineAssessmentRetired,
)


class OnlineAssessment(AggregateRoot):
    """
    Online Assessment aggregate root.
    
    Represents an online assessment linked to a questionnaire.
    """
    
    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        RETIRED = "retired", "Retired"
    
    class TargetType(models.TextChoices):
        THIRD_PARTY = "third_party", "Third Party"
        ORG_UNIT = "org_unit", "Organizational Unit"
        SERVICE = "service", "Service"
        ASSET = "asset", "Asset"
        PROCESS = "process", "Process"
    
    # Basic fields
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    # Questionnaire reference
    questionnaireId = models.UUIDField(db_index=True, help_text="ID of the questionnaire")
    
    # Target type
    target_type = models.CharField(
        max_length=50,
        choices=TargetType.choices,
        db_index=True,
        help_text="Type of entity this assessment targets"
    )
    
    # Scoring
    scoring_model = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Scoring model for the assessment"
    )
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.DRAFT,
        db_index=True
    )
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "compliance_online_assessments"
        verbose_name = "Online Assessment"
        verbose_name_plural = "Online Assessments"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["questionnaireId"]),
            models.Index(fields=["target_type"]),
        ]
    
    def create(self, name: str, questionnaire_id: uuid.UUID, target_type: str,
               description: str = None, scoring_model: str = None):
        """
        Create a new online assessment.
        
        Domain method that enforces business rules and raises events.
        """
        self.name = name
        self.description = description
        self.questionnaireId = questionnaire_id
        self.target_type = target_type
        self.scoring_model = scoring_model
        self.lifecycle_state = self.LifecycleState.DRAFT
        
        event = OnlineAssessmentCreated()
        event.payload = {
            "assessment_id": str(self.id),
            "name": name,
            "questionnaire_id": str(questionnaire_id),
        }
        self._raise_event(event)
    
    def publish(self):
        """Publish the assessment"""
        if self.lifecycle_state != self.LifecycleState.PUBLISHED:
            self.lifecycle_state = self.LifecycleState.PUBLISHED
            
            event = OnlineAssessmentPublished()
            event.payload = {
                "assessment_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def retire(self):
        """Retire the assessment"""
        if self.lifecycle_state != self.LifecycleState.RETIRED:
            self.lifecycle_state = self.LifecycleState.RETIRED
            
            event = OnlineAssessmentRetired()
            event.payload = {
                "assessment_id": str(self.id),
                "name": self.name,
            }
            self._raise_event(event)
    
    def __str__(self):
        return self.name

