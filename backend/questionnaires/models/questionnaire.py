"""
Questionnaire Aggregate

Aggregate for managing questionnaires with dynamic question flows
and conditional logic for guided assessments.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class Questionnaire(AggregateRoot):
    """
    Questionnaire aggregate for guided assessment workflows.

    Supports dynamic question flows with conditional logic,
    scoring, and progress tracking.
    """

    # Basic information
    title = models.CharField(
        max_length=255,
        help_text="Questionnaire title"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Questionnaire description"
    )

    # Questionnaire type and category
    QUESTIONNAIRE_TYPES = [
        ('assessment', 'Assessment'),
        ('survey', 'Survey'),
        ('audit', 'Audit'),
        ('compliance', 'Compliance Check'),
        ('risk', 'Risk Assessment'),
        ('custom', 'Custom'),
    ]

    questionnaire_type = models.CharField(
        max_length=20,
        choices=QUESTIONNAIRE_TYPES,
        default='assessment',
        help_text="Type of questionnaire"
    )

    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Questionnaire category (e.g., 'Security', 'Compliance')"
    )

    # Lifecycle
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Questionnaire lifecycle status"
    )

    # Versioning
    questionnaire_version = models.CharField(
        max_length=20,
        default='1.0',
        help_text="Questionnaire version"
    )

    # Timing and scheduling
    estimated_duration_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Estimated completion time in minutes"
    )

    # Access control
    is_public = models.BooleanField(
        default=False,
        help_text="Whether questionnaire is publicly accessible"
    )

    requires_authentication = models.BooleanField(
        default=True,
        help_text="Whether authentication is required"
    )

    # Scoring and results
    enable_scoring = models.BooleanField(
        default=True,
        help_text="Whether questionnaire supports scoring"
    )

    passing_score_percentage = models.IntegerField(
        null=True,
        blank=True,
        help_text="Minimum passing score percentage (if scoring enabled)"
    )

    # Question flow configuration
    enable_conditional_logic = models.BooleanField(
        default=True,
        help_text="Whether conditional question logic is enabled"
    )

    allow_back_navigation = models.BooleanField(
        default=True,
        help_text="Whether users can navigate backwards"
    )

    show_progress_bar = models.BooleanField(
        default=True,
        help_text="Whether to show progress indicator"
    )

    # Content and structure
    introduction_text = models.TextField(
        blank=True,
        null=True,
        help_text="Introduction text shown before questionnaire starts"
    )

    completion_message = models.TextField(
        blank=True,
        null=True,
        help_text="Message shown upon completion"
    )

    # Metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Questionnaire tags for organization"
    )

    # Usage tracking
    usage_count = models.IntegerField(
        default=0,
        help_text="Number of times questionnaire has been taken"
    )

    average_completion_time = models.IntegerField(
        null=True,
        blank=True,
        help_text="Average completion time in minutes"
    )

    # Relationships
    question_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of question IDs in this questionnaire"
    )

    class Meta:
        db_table = "questionnaires"
        indexes = [
            models.Index(fields=['status', 'questionnaire_type'], name='questionnaire_status_type_idx'),
            models.Index(fields=['category'], name='questionnaire_category_idx'),
            models.Index(fields=['created_at'], name='questionnaire_created_idx'),
            models.Index(fields=['usage_count'], name='questionnaire_usage_idx'),
        ]
        ordering = ['-created_at']

    def create_questionnaire(
        self,
        title: str,
        questionnaire_type: str = 'assessment',
        description: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new questionnaire"""
        self.title = title
        self.questionnaire_type = questionnaire_type
        self.description = description
        self.category = category
        self.tags = tags if tags is not None else []
        self.status = 'draft'

        from .domain_events import QuestionnaireCreated
        self._raise_event(QuestionnaireCreated(
            aggregate_id=self.id,
            title=title,
            questionnaire_type=questionnaire_type
        ))

    def publish(self):
        """Publish the questionnaire"""
        if self.status == 'draft':
            self.status = 'published'

            from .domain_events import QuestionnairePublished
            self._raise_event(QuestionnairePublished(
                aggregate_id=self.id,
                title=self.title
            ))

    def archive(self):
        """Archive the questionnaire"""
        if self.status == 'published':
            self.status = 'archived'

            from .domain_events import QuestionnaireArchived
            self._raise_event(QuestionnaireArchived(
                aggregate_id=self.id,
                title=self.title
            ))

    def add_question(self, question_id: str, position: Optional[int] = None):
        """Add a question to the questionnaire"""
        if question_id not in self.question_ids:
            if position is None:
                self.question_ids.append(question_id)
            else:
                self.question_ids.insert(position, question_id)

            from .domain_events import QuestionAddedToQuestionnaire
            self._raise_event(QuestionAddedToQuestionnaire(
                aggregate_id=self.id,
                question_id=question_id,
                position=len(self.question_ids) - 1
            ))

    def remove_question(self, question_id: str):
        """Remove a question from the questionnaire"""
        if question_id in self.question_ids:
            position = self.question_ids.index(question_id)
            self.question_ids.remove(question_id)

            from .domain_events import QuestionRemovedFromQuestionnaire
            self._raise_event(QuestionRemovedFromQuestionnaire(
                aggregate_id=self.id,
                question_id=question_id,
                position=position
            ))

    def reorder_questions(self, question_ids: List[str]):
        """Reorder questions in the questionnaire"""
        # Validate that all provided IDs exist in current questions
        current_set = set(self.question_ids)
        new_set = set(question_ids)

        if current_set != new_set:
            raise ValueError("Question IDs do not match current questionnaire questions")

        old_order = self.question_ids.copy()
        self.question_ids = question_ids

        from .domain_events import QuestionnaireQuestionsReordered
        self._raise_event(QuestionnaireQuestionsReordered(
            aggregate_id=self.id,
            old_order=old_order,
            new_order=question_ids
        ))

    def record_usage(self, completion_time_minutes: Optional[int] = None):
        """Record questionnaire usage for analytics"""
        self.usage_count += 1

        if completion_time_minutes is not None:
            # Update rolling average
            if self.average_completion_time is None:
                self.average_completion_time = completion_time_minutes
            else:
                # Simple moving average calculation
                total_completions = max(1, self.usage_count - 1)  # Don't count current
                self.average_completion_time = int(
                    (self.average_completion_time * total_completions + completion_time_minutes) / self.usage_count
                )

    def clone(self, new_title: Optional[str] = None, new_version: Optional[str] = None) -> 'Questionnaire':
        """Create a copy of this questionnaire"""
        clone = Questionnaire()

        # Copy all fields except ID and timestamps
        clone.title = new_title or f"Copy of {self.title}"
        clone.description = self.description
        clone.questionnaire_type = self.questionnaire_type
        clone.category = self.category
        clone.status = 'draft'
        clone.questionnaire_version = new_version or self.questionnaire_version
        clone.estimated_duration_minutes = self.estimated_duration_minutes
        clone.is_public = self.is_public
        clone.requires_authentication = self.requires_authentication
        clone.enable_scoring = self.enable_scoring
        clone.passing_score_percentage = self.passing_score_percentage
        clone.enable_conditional_logic = self.enable_conditional_logic
        clone.allow_back_navigation = self.allow_back_navigation
        clone.show_progress_bar = self.show_progress_bar
        clone.introduction_text = self.introduction_text
        clone.completion_message = self.completion_message
        clone.tags = self.tags.copy()
        clone.question_ids = self.question_ids.copy()  # Copy question references

        from .domain_events import QuestionnaireCloned
        clone._raise_event(QuestionnaireCloned(
            aggregate_id=clone.id,
            original_questionnaire_id=self.id,
            title=clone.title
        ))

        return clone

    @property
    def question_count(self) -> int:
        """Get the number of questions in this questionnaire"""
        return len(self.question_ids)

    @property
    def is_scored(self) -> bool:
        """Check if this questionnaire supports scoring"""
        return self.enable_scoring

    @property
    def has_conditional_logic(self) -> bool:
        """Check if this questionnaire has conditional logic"""
        return self.enable_conditional_logic

    def __str__(self):
        return f"Questionnaire({self.title} - {self.question_count} questions)"
