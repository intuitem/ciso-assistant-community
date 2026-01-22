"""
Question Aggregate

Aggregate for managing individual questions within questionnaires,
with support for multiple question types and conditional logic.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class Question(AggregateRoot):
    """
    Question aggregate for questionnaire questions.

    Supports multiple question types with validation, scoring,
    and conditional logic capabilities.
    """

    # Basic question information
    text = models.TextField(
        help_text="The question text"
    )

    help_text = models.TextField(
        blank=True,
        null=True,
        help_text="Help text or additional context for the question"
    )

    # Question type
    QUESTION_TYPES = [
        ('text', 'Text Input'),
        ('textarea', 'Text Area'),
        ('single_choice', 'Single Choice (Radio)'),
        ('multiple_choice', 'Multiple Choice (Checkbox)'),
        ('select', 'Dropdown Select'),
        ('rating', 'Rating Scale'),
        ('yes_no', 'Yes/No'),
        ('date', 'Date'),
        ('number', 'Number'),
        ('email', 'Email'),
        ('url', 'URL'),
        ('file_upload', 'File Upload'),
    ]

    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default='text',
        help_text="Type of question input"
    )

    # Question options (for choice-type questions)
    options = models.JSONField(
        default=list,
        blank=True,
        help_text="List of options for choice questions (e.g., [{'value': 'yes', 'label': 'Yes', 'score': 1}])"
    )

    # Validation rules
    is_required = models.BooleanField(
        default=False,
        help_text="Whether this question must be answered"
    )

    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="Validation rules (e.g., {'min_length': 5, 'max_length': 100, 'pattern': 'regex'})"
    )

    # Scoring (for scored questionnaires)
    enable_scoring = models.BooleanField(
        default=False,
        help_text="Whether this question contributes to scoring"
    )

    points = models.IntegerField(
        default=0,
        help_text="Points awarded for correct/best answer"
    )

    # Conditional logic
    conditional_logic = models.JSONField(
        default=dict,
        blank=True,
        help_text="Conditional logic rules (e.g., {'show_if': {'question_id': 'q1', 'operator': 'equals', 'value': 'yes'}})"
    )

    # Dependencies
    depends_on_question_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of question IDs this question depends on"
    )

    # Ordering and grouping
    order = models.IntegerField(
        default=0,
        help_text="Display order within questionnaire"
    )

    section = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Section or grouping name"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this question is active/available"
    )

    # Metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Question tags for organization"
    )

    # Usage analytics
    times_asked = models.IntegerField(
        default=0,
        help_text="Number of times this question has been presented"
    )

    skip_rate = models.FloatField(
        default=0.0,
        help_text="Percentage of times this question is skipped"
    )

    class Meta:
        db_table = "questions"
        indexes = [
            models.Index(fields=['question_type'], name='question_type_idx'),
            models.Index(fields=['is_active'], name='question_active_idx'),
            models.Index(fields=['order'], name='question_order_idx'),
            models.Index(fields=['section'], name='question_section_idx'),
        ]
        ordering = ['order', 'created_at']

    def create_question(
        self,
        text: str,
        question_type: str = 'text',
        help_text: Optional[str] = None,
        options: Optional[List[Dict[str, Any]]] = None,
        is_required: bool = False,
        tags: Optional[List[str]] = None
    ):
        """Create a new question"""
        self.text = text
        self.question_type = question_type
        self.help_text = help_text
        self.options = options if options is not None else []
        self.is_required = is_required
        self.tags = tags if tags is not None else []
        self.is_active = True

        from .domain_events import QuestionCreated
        self._raise_event(QuestionCreated(
            aggregate_id=self.id,
            question_type=question_type,
            text=text[:100]  # Truncate for event
        ))

    def update_question(
        self,
        text: Optional[str] = None,
        help_text: Optional[str] = None,
        options: Optional[List[Dict[str, Any]]] = None,
        validation_rules: Optional[Dict[str, Any]] = None,
        conditional_logic: Optional[Dict[str, Any]] = None
    ):
        """Update question properties"""
        old_data = {
            'text': self.text,
            'help_text': self.help_text,
            'options': self.options.copy(),
            'validation_rules': self.validation_rules.copy(),
            'conditional_logic': self.conditional_logic.copy()
        }

        if text is not None:
            self.text = text
        if help_text is not None:
            self.help_text = help_text
        if options is not None:
            self.options = options
        if validation_rules is not None:
            self.validation_rules = validation_rules
        if conditional_logic is not None:
            self.conditional_logic = conditional_logic

        from .domain_events import QuestionUpdated
        self._raise_event(QuestionUpdated(
            aggregate_id=self.id,
            changes={
                'text': text is not None,
                'help_text': help_text is not None,
                'options': options is not None,
                'validation_rules': validation_rules is not None,
                'conditional_logic': conditional_logic is not None
            }
        ))

    def set_scoring(self, enable_scoring: bool, points: int = 0):
        """Configure scoring for this question"""
        self.enable_scoring = enable_scoring
        self.points = points

    def add_option(self, value: str, label: str, score: int = 0, order: Optional[int] = None):
        """Add an option to a choice-type question"""
        if not self._supports_options():
            raise ValueError(f"Question type '{self.question_type}' does not support options")

        option = {
            'value': value,
            'label': label,
            'score': score,
            'order': order or len(self.options)
        }

        # Remove existing option with same value if present
        self.options = [opt for opt in self.options if opt.get('value') != value]
        self.options.append(option)

        # Sort by order
        self.options.sort(key=lambda x: x.get('order', 999))

    def remove_option(self, value: str):
        """Remove an option from the question"""
        self.options = [opt for opt in self.options if opt.get('value') != value]

    def add_dependency(self, question_id: str):
        """Add a dependency on another question"""
        if question_id not in self.depends_on_question_ids:
            self.depends_on_question_ids.append(question_id)

    def remove_dependency(self, question_id: str):
        """Remove a dependency"""
        if question_id in self.depends_on_question_ids:
            self.depends_on_question_ids.remove(question_id)

    def set_conditional_logic(self, logic: Dict[str, Any]):
        """Set conditional display logic"""
        self.conditional_logic = logic

    def validate_answer(self, answer_value: Any) -> Dict[str, Any]:
        """
        Validate an answer against question rules.

        Returns validation result with errors and warnings.
        """
        errors = []
        warnings = []

        # Check required
        if self.is_required and (answer_value is None or answer_value == ''):
            errors.append("This question is required")

        # Type-specific validation
        if answer_value is not None and answer_value != '':
            type_validation = self._validate_answer_type(answer_value)
            errors.extend(type_validation.get('errors', []))
            warnings.extend(type_validation.get('warnings', []))

        # Option validation for choice questions
        if self._supports_options():
            option_validation = self._validate_answer_options(answer_value)
            errors.extend(option_validation.get('errors', []))
            warnings.extend(option_validation.get('warnings', []))

        # Custom validation rules
        rule_validation = self._validate_custom_rules(answer_value)
        errors.extend(rule_validation.get('errors', []))
        warnings.extend(rule_validation.get('warnings', []))

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def calculate_score(self, answer_value: Any) -> int:
        """
        Calculate score for the given answer.

        Returns points awarded for this question.
        """
        if not self.enable_scoring:
            return 0

        if self._supports_options() and answer_value is not None:
            # Find the option and return its score
            for option in self.options:
                if option.get('value') == answer_value:
                    return option.get('score', 0)

        # For non-choice questions, return base points if answered
        if answer_value is not None and answer_value != '':
            return self.points

        return 0

    def record_usage(self, was_skipped: bool = False):
        """Record question usage for analytics"""
        self.times_asked += 1

        if was_skipped:
            self.skip_rate = ((self.skip_rate * (self.times_asked - 1)) + 1) / self.times_asked
        else:
            self.skip_rate = (self.skip_rate * (self.times_asked - 1)) / self.times_asked

    def _supports_options(self) -> bool:
        """Check if this question type supports options"""
        return self.question_type in ['single_choice', 'multiple_choice', 'select', 'rating']

    def _validate_answer_type(self, answer_value: Any) -> Dict[str, Any]:
        """Validate answer type matches question type"""
        errors = []
        warnings = []

        try:
            if self.question_type == 'number':
                float(answer_value)
            elif self.question_type == 'email':
                # Basic email validation
                if '@' not in str(answer_value):
                    errors.append("Invalid email format")
            elif self.question_type == 'url':
                # Basic URL validation
                if not str(answer_value).startswith(('http://', 'https://')):
                    warnings.append("URL should start with http:// or https://")
            elif self.question_type == 'date':
                # Try to parse as date
                from datetime import datetime
                datetime.fromisoformat(str(answer_value))
        except (ValueError, TypeError):
            errors.append(f"Invalid {self.question_type} format")

        return {'errors': errors, 'warnings': warnings}

    def _validate_answer_options(self, answer_value: Any) -> Dict[str, Any]:
        """Validate answer against available options"""
        errors = []
        warnings = []

        if self.question_type == 'multiple_choice':
            # answer_value should be a list
            if not isinstance(answer_value, list):
                errors.append("Multiple choice answers must be a list")
                return {'errors': errors, 'warnings': warnings}

            for value in answer_value:
                if not any(opt.get('value') == value for opt in self.options):
                    errors.append(f"Invalid option: {value}")
        else:
            # Single choice
            if answer_value is not None and not any(opt.get('value') == answer_value for opt in self.options):
                errors.append(f"Invalid option: {answer_value}")

        return {'errors': errors, 'warnings': warnings}

    def _validate_custom_rules(self, answer_value: Any) -> Dict[str, Any]:
        """Validate against custom validation rules"""
        errors = []
        warnings = []

        rules = self.validation_rules

        if not rules:
            return {'errors': errors, 'warnings': warnings}

        # Min/max length
        if 'min_length' in rules and len(str(answer_value)) < rules['min_length']:
            errors.append(f"Answer must be at least {rules['min_length']} characters")

        if 'max_length' in rules and len(str(answer_value)) > rules['max_length']:
            errors.append(f"Answer must be at most {rules['max_length']} characters")

        # Pattern matching
        if 'pattern' in rules:
            import re
            if not re.match(rules['pattern'], str(answer_value)):
                errors.append("Answer format is invalid")

        # Numeric ranges
        if self.question_type == 'number':
            try:
                num_value = float(answer_value)
                if 'min_value' in rules and num_value < rules['min_value']:
                    errors.append(f"Value must be at least {rules['min_value']}")
                if 'max_value' in rules and num_value > rules['max_value']:
                    errors.append(f"Value must be at most {rules['max_value']}")
            except (ValueError, TypeError):
                pass  # Type validation already handled

        return {'errors': errors, 'warnings': warnings}

    @property
    def has_options(self) -> bool:
        """Check if question has options configured"""
        return len(self.options) > 0

    @property
    def has_dependencies(self) -> bool:
        """Check if question has dependencies"""
        return len(self.depends_on_question_ids) > 0

    @property
    def has_conditional_logic(self) -> bool:
        """Check if question has conditional display logic"""
        return bool(self.conditional_logic)

    def __str__(self):
        return f"Question({self.question_type}: {self.text[:50]}...)"
