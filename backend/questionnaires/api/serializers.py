"""
DRF Serializers for Questionnaires module
"""

from rest_framework import serializers
from ..models.questionnaire import Questionnaire
from ..models.question import Question
from ..models.questionnaire_run import QuestionnaireRun


class QuestionnaireSerializer(serializers.ModelSerializer):
    """Serializer for Questionnaire aggregate"""

    # Computed fields
    question_count = serializers.ReadOnlyField()
    is_scored = serializers.ReadOnlyField()
    has_conditional_logic = serializers.ReadOnlyField()

    class Meta:
        model = Questionnaire
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'title', 'description', 'questionnaire_type', 'category',
            'status', 'questionnaire_version',
            'estimated_duration_minutes', 'is_public', 'requires_authentication',
            'enable_scoring', 'passing_score_percentage',
            'enable_conditional_logic', 'allow_back_navigation', 'show_progress_bar',
            'introduction_text', 'completion_message',
            'tags', 'usage_count', 'average_completion_time',
            'question_ids',
            'question_count', 'is_scored', 'has_conditional_logic',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at', 'usage_count', 'average_completion_time']

    def create(self, validated_data):
        """Create a new questionnaire"""
        questionnaire = Questionnaire()
        questionnaire.create_questionnaire(
            title=validated_data['title'],
            questionnaire_type=validated_data.get('questionnaire_type', 'assessment'),
            description=validated_data.get('description'),
            category=validated_data.get('category'),
            tags=validated_data.get('tags', [])
        )

        # Set additional fields
        for field in ['estimated_duration_minutes', 'is_public', 'requires_authentication',
                     'enable_scoring', 'passing_score_percentage', 'enable_conditional_logic',
                     'allow_back_navigation', 'show_progress_bar', 'introduction_text',
                     'completion_message']:
            if field in validated_data:
                setattr(questionnaire, field, validated_data[field])

        questionnaire.save()
        return questionnaire

    def update(self, instance, validated_data):
        """Update an existing questionnaire"""
        for field in ['title', 'description', 'questionnaire_type', 'category',
                     'questionnaire_version', 'estimated_duration_minutes', 'is_public',
                     'requires_authentication', 'enable_scoring', 'passing_score_percentage',
                     'enable_conditional_logic', 'allow_back_navigation', 'show_progress_bar',
                     'introduction_text', 'completion_message', 'tags']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        instance.save()
        return instance


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for Question aggregate"""

    # Computed fields
    has_options = serializers.ReadOnlyField()
    has_dependencies = serializers.ReadOnlyField()
    has_conditional_logic = serializers.ReadOnlyField()

    class Meta:
        model = Question
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'text', 'help_text', 'question_type', 'options',
            'is_required', 'validation_rules',
            'enable_scoring', 'points',
            'conditional_logic', 'depends_on_question_ids',
            'order', 'section', 'is_active', 'tags',
            'times_asked', 'skip_rate',
            'has_options', 'has_dependencies', 'has_conditional_logic',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at', 'times_asked', 'skip_rate']

    def create(self, validated_data):
        """Create a new question"""
        question = Question()
        question.create_question(
            text=validated_data['text'],
            question_type=validated_data.get('question_type', 'text'),
            help_text=validated_data.get('help_text'),
            options=validated_data.get('options', []),
            is_required=validated_data.get('is_required', False),
            tags=validated_data.get('tags', [])
        )

        # Set additional fields
        for field in ['validation_rules', 'enable_scoring', 'points',
                     'conditional_logic', 'depends_on_question_ids',
                     'order', 'section']:
            if field in validated_data:
                setattr(question, field, validated_data[field])

        question.save()
        return question

    def update(self, instance, validated_data):
        """Update an existing question"""
        for field in ['text', 'help_text', 'question_type', 'options',
                     'is_required', 'validation_rules', 'enable_scoring', 'points',
                     'conditional_logic', 'depends_on_question_ids',
                     'order', 'section', 'is_active', 'tags']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        instance.save()
        return instance


class QuestionnaireRunSerializer(serializers.ModelSerializer):
    """Serializer for QuestionnaireRun aggregate"""

    # Computed fields
    duration_seconds = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    is_in_progress = serializers.ReadOnlyField()
    score_percentage = serializers.ReadOnlyField()
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = QuestionnaireRun
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'questionnaire_id', 'user_id', 'status',
            'current_question_index', 'questions_answered', 'total_questions',
            'started_at', 'completed_at', 'time_spent_seconds',
            'answers', 'enable_scoring', 'current_score', 'max_possible_score',
            'passing_score', 'visible_question_ids', 'answered_question_ids',
            'skipped_question_ids', 'conditional_state',
            'session_token', 'expires_at',
            'final_score_percentage', 'passed', 'feedback',
            'duration_seconds', 'is_completed', 'is_in_progress',
            'score_percentage', 'progress_percentage',
        ]
        read_only_fields = [
            'id', 'version', 'created_at', 'updated_at',
            'started_at', 'completed_at', 'time_spent_seconds',
            'questions_answered', 'current_score', 'max_possible_score',
            'answered_question_ids', 'skipped_question_ids',
            'final_score_percentage', 'passed',
        ]

    def get_progress_percentage(self, obj):
        return obj.get_progress_percentage()

    def create(self, validated_data):
        """Create a new questionnaire run"""
        run = QuestionnaireRun()
        run.start_run(
            questionnaire_id=validated_data['questionnaire_id'],
            user_id=validated_data.get('user_id'),
            session_token=validated_data.get('session_token'),
            enable_scoring=validated_data.get('enable_scoring', False),
            expires_at=validated_data.get('expires_at')
        )

        run.save()
        return run


class AnswerSubmissionSerializer(serializers.Serializer):
    """Serializer for submitting answers"""
    question_id = serializers.CharField()
    answer_value = serializers.JSONField()
    time_spent = serializers.IntegerField(default=0)
