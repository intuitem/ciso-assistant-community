"""
AssessmentRun Association

First-class association representing a run of an assessment.
"""

import uuid
from typing import Optional, List
from datetime import datetime
from django.db import models
from django.utils import timezone

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    AssessmentRunInvited,
    AssessmentRunStarted,
    AssessmentRunSubmitted,
    AssessmentRunReviewed,
    AssessmentRunClosed,
)


class AssessmentRun(AggregateRoot):
    """
    Assessment Run association.
    
    First-class entity representing a run of an assessment with scope, answers, review, and scoring.
    """
    
    class LifecycleState(models.TextChoices):
        INVITED = "invited", "Invited"
        IN_PROGRESS = "in_progress", "In Progress"
        SUBMITTED = "submitted", "Submitted"
        REVIEWED = "reviewed", "Reviewed"
        CLOSED = "closed", "Closed"
    
    class TargetType(models.TextChoices):
        THIRD_PARTY = "third_party", "Third Party"
        ORG_UNIT = "org_unit", "Organizational Unit"
        SERVICE = "service", "Service"
        ASSET = "asset", "Asset"
        PROCESS = "process", "Process"
    
    # Assessment and target
    assessmentId = models.UUIDField(db_index=True, help_text="ID of the assessment")
    target_type = models.CharField(
        max_length=50,
        choices=TargetType.choices,
        db_index=True
    )
    target_id = models.UUIDField(db_index=True)
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.INVITED,
        db_index=True
    )
    
    # Embedded ID arrays
    invitedUserIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of invited user IDs"
    )
    respondentUserIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of respondent user IDs"
    )
    findingIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of finding IDs"
    )
    evidenceIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of evidence IDs"
    )
    
    # Dates and scoring
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    score = models.FloatField(null=True, blank=True, help_text="Assessment score")
    
    # Answers (stored as JSON array of Answer value objects)
    answers = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of answers: [{questionId, value, notes}]"
    )
    
    # Additional fields
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = "compliance_assessment_runs"
        verbose_name = "Assessment Run"
        verbose_name_plural = "Assessment Runs"
        indexes = [
            models.Index(fields=["assessmentId", "target_type", "target_id"]),
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["submitted_at"]),
        ]
    
    def create(self, assessment_id: uuid.UUID, target_type: str, target_id: uuid.UUID,
               invited_user_ids: List[uuid.UUID] = None):
        """
        Create a new assessment run.
        
        Domain method that enforces business rules and raises events.
        """
        self.assessmentId = assessment_id
        self.target_type = target_type
        self.target_id = target_id
        self.invitedUserIds = invited_user_ids or []
        self.lifecycle_state = self.LifecycleState.INVITED
        
        event = AssessmentRunInvited()
        event.payload = {
            "run_id": str(self.id),
            "assessment_id": str(assessment_id),
            "target_type": target_type,
            "target_id": str(target_id),
        }
        self._raise_event(event)
    
    def start(self, respondent_user_id: uuid.UUID):
        """Start the assessment run"""
        if self.lifecycle_state == self.LifecycleState.INVITED:
            if respondent_user_id not in self.respondentUserIds:
                self.respondentUserIds.append(respondent_user_id)
            
            self.started_at = timezone.now()
            self.lifecycle_state = self.LifecycleState.IN_PROGRESS
            
            event = AssessmentRunStarted()
            event.payload = {
                "run_id": str(self.id),
                "respondent_user_id": str(respondent_user_id),
            }
            self._raise_event(event)
    
    def submit(self, answers: List[dict] = None, score: float = None):
        """
        Submit the assessment run.
        
        Args:
            answers: List of answer dictionaries
            score: Optional calculated score
        """
        if self.lifecycle_state == self.LifecycleState.IN_PROGRESS:
            if answers:
                self.answers = answers
            if score is not None:
                self.score = score
            
            self.submitted_at = timezone.now()
            self.lifecycle_state = self.LifecycleState.SUBMITTED
            
            event = AssessmentRunSubmitted()
            event.payload = {
                "run_id": str(self.id),
                "score": score,
            }
            self._raise_event(event)
    
    def review(self):
        """Review the assessment run"""
        if self.lifecycle_state == self.LifecycleState.SUBMITTED:
            self.lifecycle_state = self.LifecycleState.REVIEWED
            
            event = AssessmentRunReviewed()
            event.payload = {
                "run_id": str(self.id),
            }
            self._raise_event(event)
    
    def close(self):
        """Close the assessment run"""
        if self.lifecycle_state != self.LifecycleState.CLOSED:
            self.lifecycle_state = self.LifecycleState.CLOSED
            
            event = AssessmentRunClosed()
            event.payload = {
                "run_id": str(self.id),
            }
            self._raise_event(event)
    
    def add_answer(self, question_id: str, value, notes: str = None):
        """Add or update an answer"""
        # Remove existing answer for this question if any
        self.answers = [a for a in self.answers if a.get("questionId") != question_id]
        
        # Add new answer
        answer = {
            "questionId": question_id,
            "value": value,
            "notes": notes,
        }
        self.answers.append(answer)
    
    def add_finding(self, finding_id: uuid.UUID):
        """Add a finding to this assessment run"""
        if finding_id not in self.findingIds:
            self.findingIds.append(finding_id)
    
    def add_evidence(self, evidence_id: uuid.UUID):
        """Add evidence to this assessment run"""
        if evidence_id not in self.evidenceIds:
            self.evidenceIds.append(evidence_id)
    
    def __str__(self):
        return f"Assessment {self.assessmentId} on {self.target_type} {self.target_id} ({self.lifecycle_state})"

