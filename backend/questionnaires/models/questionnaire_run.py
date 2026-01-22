"""
QuestionnaireRun Aggregate

Aggregate for tracking individual questionnaire completions,
answers, scoring, and progress through dynamic question flows.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class QuestionnaireRun(AggregateRoot):
    """
    QuestionnaireRun aggregate for tracking questionnaire completions.

    Manages the state of an individual questionnaire completion,
    including answers, progress, scoring, and conditional logic.
    """

    # Relationships
    questionnaire_id = models.UUIDField(
        db_index=True,
        help_text="ID of the questionnaire being taken"
    )

    user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID of the user taking the questionnaire (null for anonymous)"
    )

    # Run status
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
        ('expired', 'Expired'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_progress',
        help_text="Current status of the questionnaire run"
    )

    # Progress tracking
    current_question_index = models.IntegerField(
        default=0,
        help_text="Index of the current question being answered"
    )

    questions_answered = models.IntegerField(
        default=0,
        help_text="Number of questions answered so far"
    )

    total_questions = models.IntegerField(
        default=0,
        help_text="Total number of questions in this run (may vary due to conditional logic)"
    )

    # Timing
    started_at = models.DateTimeField(
        default=timezone.now,
        help_text="When the questionnaire run was started"
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the questionnaire run was completed"
    )

    time_spent_seconds = models.IntegerField(
        default=0,
        help_text="Total time spent on questionnaire in seconds"
    )

    # Answers storage
    answers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dictionary of question_id -> answer_value mappings"
    )

    # Scoring (if questionnaire supports scoring)
    enable_scoring = models.BooleanField(
        default=False,
        help_text="Whether this run supports scoring"
    )

    current_score = models.IntegerField(
        default=0,
        help_text="Current score accumulated"
    )

    max_possible_score = models.IntegerField(
        default=0,
        help_text="Maximum possible score for this run"
    )

    passing_score = models.IntegerField(
        null=True,
        blank=True,
        help_text="Minimum passing score (if applicable)"
    )

    # Question flow state
    visible_question_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of question IDs visible to the user"
    )

    answered_question_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of question IDs that have been answered"
    )

    skipped_question_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of question IDs that were skipped"
    )

    # Conditional logic state
    conditional_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="Current state for conditional logic evaluation"
    )

    # Session management
    session_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Token for resuming anonymous sessions"
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this run expires (for time-limited questionnaires)"
    )

    # Metadata
    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text="Browser/client user agent"
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Client IP address"
    )

    # Results and feedback
    final_score_percentage = models.FloatField(
        null=True,
        blank=True,
        help_text="Final score as percentage"
    )

    passed = models.BooleanField(
        null=True,
        blank=True,
        help_text="Whether the run passed (if scoring enabled)"
    )

    feedback = models.TextField(
        blank=True,
        null=True,
        help_text="User feedback or comments"
    )

    class Meta:
        db_table = "questionnaire_runs"
        indexes = [
            models.Index(fields=['questionnaire_id', 'status'], name='run_questionnaire_status_idx'),
            models.Index(fields=['user_id', 'status'], name='run_user_status_idx'),
            models.Index(fields=['status', 'started_at'], name='run_status_started_idx'),
            models.Index(fields=['session_token'], name='run_session_token_idx'),
            models.Index(fields=['expires_at'], name='run_expires_idx'),
        ]
        ordering = ['-started_at']

    def start_run(
        self,
        questionnaire_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        session_token: Optional[str] = None,
        enable_scoring: bool = False,
        expires_at: Optional[timezone.datetime] = None
    ):
        """Start a new questionnaire run"""
        self.questionnaire_id = questionnaire_id
        self.user_id = user_id
        self.session_token = session_token
        self.enable_scoring = enable_scoring
        self.expires_at = expires_at
        self.status = 'in_progress'
        self.started_at = timezone.now()

        from .domain_events import QuestionnaireRunStarted
        self._raise_event(QuestionnaireRunStarted(
            aggregate_id=self.id,
            questionnaire_id=str(questionnaire_id),
            user_id=str(user_id) if user_id else None
        ))

    def submit_answer(self, question_id: str, answer_value: Any, time_spent: int = 0):
        """
        Submit an answer for a question.

        Args:
            question_id: ID of the question being answered
            answer_value: The answer value
            time_spent: Time spent on this question in seconds
        """
        # Store the answer
        self.answers[question_id] = {
            'value': answer_value,
            'timestamp': timezone.now().isoformat(),
            'time_spent_seconds': time_spent
        }

        # Update progress tracking
        if question_id not in self.answered_question_ids:
            self.answered_question_ids.append(question_id)
            self.questions_answered += 1

        # Remove from skipped if it was there
        if question_id in self.skipped_question_ids:
            self.skipped_question_ids.remove(question_id)

        # Update time spent
        self.time_spent_seconds += time_spent

        # Update conditional state
        self._update_conditional_state(question_id, answer_value)

        from .domain_events import AnswerSubmitted
        self._raise_event(AnswerSubmitted(
            aggregate_id=self.id,
            question_id=question_id,
            answer_value=str(answer_value)[:100]  # Truncate for event
        ))

    def skip_question(self, question_id: str):
        """Skip a question without answering"""
        if question_id not in self.answered_question_ids and question_id not in self.skipped_question_ids:
            self.skipped_question_ids.append(question_id)

    def update_progress(self, current_question_index: int, visible_questions: List[str]):
        """Update progress through the questionnaire"""
        self.current_question_index = current_question_index
        self.visible_question_ids = visible_questions
        self.total_questions = len(visible_questions)

    def calculate_score(self) -> Dict[str, Any]:
        """
        Calculate the current score for this run.

        Returns scoring information including current score,
        max possible, and pass/fail status.
        """
        if not self.enable_scoring:
            return {
                'enabled': False,
                'current_score': 0,
                'max_possible_score': 0,
                'percentage': 0.0,
                'passed': None
            }

        # Calculate score based on answers
        total_score = 0
        max_score = 0

        # This would need access to question definitions to calculate properly
        # For now, return placeholder logic
        for answer_data in self.answers.values():
            # Placeholder scoring logic
            total_score += 1  # Simple scoring
            max_score += 1

        percentage = (total_score / max_score * 100) if max_score > 0 else 0.0

        passed = None
        if self.passing_score is not None:
            passed = total_score >= self.passing_score

        self.current_score = total_score
        self.max_possible_score = max_score
        self.final_score_percentage = percentage
        self.passed = passed

        return {
            'enabled': True,
            'current_score': total_score,
            'max_possible_score': max_score,
            'percentage': round(percentage, 2),
            'passed': passed
        }

    def complete_run(self, feedback: Optional[str] = None):
        """Mark the questionnaire run as completed"""
        if self.status == 'in_progress':
            self.status = 'completed'
            self.completed_at = timezone.now()

            # Final scoring
            if self.enable_scoring:
                self.calculate_score()

            if feedback:
                self.feedback = feedback

            # Record completion time
            if self.completed_at and self.started_at:
                duration = self.completed_at - self.started_at
                self.time_spent_seconds = int(duration.total_seconds())

            from .domain_events import QuestionnaireRunCompleted
            self._raise_event(QuestionnaireRunCompleted(
                aggregate_id=self.id,
                total_questions=self.total_questions,
                questions_answered=self.questions_answered,
                time_spent_seconds=self.time_spent_seconds,
                final_score=self.final_score_percentage
            ))

    def abandon_run(self):
        """Mark the run as abandoned"""
        if self.status == 'in_progress':
            self.status = 'abandoned'

    def expire_run(self):
        """Mark the run as expired"""
        if self.status == 'in_progress':
            self.status = 'expired'

    def get_answer(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Get the answer for a specific question"""
        return self.answers.get(question_id)

    def has_answered(self, question_id: str) -> bool:
        """Check if a question has been answered"""
        return question_id in self.answered_question_ids

    def is_expired(self) -> bool:
        """Check if this run has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    def get_progress_percentage(self) -> float:
        """Get completion progress as percentage"""
        if self.total_questions == 0:
            return 0.0
        return round((self.questions_answered / self.total_questions) * 100, 2)

    def can_navigate_back(self) -> bool:
        """Check if back navigation is allowed"""
        # This would depend on questionnaire settings
        return True  # Placeholder

    def _update_conditional_state(self, question_id: str, answer_value: Any):
        """Update conditional logic state based on answer"""
        self.conditional_state[question_id] = answer_value

    @property
    def duration_seconds(self) -> int:
        """Get total duration of the run"""
        if self.completed_at and self.started_at:
            duration = self.completed_at - self.started_at
            return int(duration.total_seconds())
        elif self.started_at:
            duration = timezone.now() - self.started_at
            return int(duration.total_seconds())
        return 0

    @property
    def is_completed(self) -> bool:
        """Check if the run is completed"""
        return self.status == 'completed'

    @property
    def is_in_progress(self) -> bool:
        """Check if the run is in progress"""
        return self.status == 'in_progress'

    @property
    def score_percentage(self) -> Optional[float]:
        """Get the final score percentage"""
        return self.final_score_percentage

    def __str__(self):
        return f"QuestionnaireRun({self.questionnaire_id} - {self.status} - {self.questions_answered}/{self.total_questions})"
