"""
API Views for Questionnaires module
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from ..models.questionnaire import Questionnaire
from ..models.question import Question
from ..models.questionnaire_run import QuestionnaireRun
from .serializers import (
    QuestionnaireSerializer,
    QuestionSerializer,
    QuestionnaireRunSerializer,
    AnswerSubmissionSerializer,
)


class QuestionnaireViewSet(viewsets.ModelViewSet):
    """ViewSet for Questionnaire aggregates"""

    queryset = Questionnaire.objects.all()
    serializer_class = QuestionnaireSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'questionnaire_type', 'category', 'is_public']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'created_at', 'usage_count']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a questionnaire"""
        questionnaire = self.get_object()
        questionnaire.publish()
        questionnaire.save()
        serializer = self.get_serializer(questionnaire)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a questionnaire"""
        questionnaire = self.get_object()
        questionnaire.archive()
        questionnaire.save()
        serializer = self.get_serializer(questionnaire)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_question(self, request, pk=None):
        """Add a question to a questionnaire"""
        questionnaire = self.get_object()
        question_id = request.data.get('question_id')
        position = request.data.get('position')
        if question_id:
            questionnaire.add_question(question_id, position)
            questionnaire.save()
            serializer = self.get_serializer(questionnaire)
            return Response(serializer.data)
        return Response({'error': 'question_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remove_question(self, request, pk=None):
        """Remove a question from a questionnaire"""
        questionnaire = self.get_object()
        question_id = request.data.get('question_id')
        if question_id:
            questionnaire.remove_question(question_id)
            questionnaire.save()
            serializer = self.get_serializer(questionnaire)
            return Response(serializer.data)
        return Response({'error': 'question_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reorder_questions(self, request, pk=None):
        """Reorder questions in a questionnaire"""
        questionnaire = self.get_object()
        question_ids = request.data.get('question_ids', [])
        if question_ids:
            try:
                questionnaire.reorder_questions(question_ids)
                questionnaire.save()
                serializer = self.get_serializer(questionnaire)
                return Response(serializer.data)
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'question_ids required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone a questionnaire"""
        questionnaire = self.get_object()
        new_title = request.data.get('title')
        new_version = request.data.get('version')
        cloned = questionnaire.clone(new_title, new_version)
        cloned.save()
        serializer = self.get_serializer(cloned)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuestionViewSet(viewsets.ModelViewSet):
    """ViewSet for Question aggregates"""

    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['question_type', 'is_active', 'is_required', 'section']
    search_fields = ['text', 'help_text']
    ordering_fields = ['order', 'created_at']
    ordering = ['order']

    @action(detail=True, methods=['post'])
    def add_option(self, request, pk=None):
        """Add an option to a question"""
        question = self.get_object()
        value = request.data.get('value')
        label = request.data.get('label')
        score = request.data.get('score', 0)
        order = request.data.get('order')
        if value and label:
            try:
                question.add_option(value, label, score, order)
                question.save()
                serializer = self.get_serializer(question)
                return Response(serializer.data)
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'value and label required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remove_option(self, request, pk=None):
        """Remove an option from a question"""
        question = self.get_object()
        value = request.data.get('value')
        if value:
            question.remove_option(value)
            question.save()
            serializer = self.get_serializer(question)
            return Response(serializer.data)
        return Response({'error': 'value required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def set_scoring(self, request, pk=None):
        """Configure scoring for a question"""
        question = self.get_object()
        enable_scoring = request.data.get('enable_scoring', False)
        points = request.data.get('points', 0)
        question.set_scoring(enable_scoring, points)
        question.save()
        serializer = self.get_serializer(question)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def validate_answer(self, request, pk=None):
        """Validate an answer against question rules"""
        question = self.get_object()
        answer_value = request.data.get('answer_value')
        result = question.validate_answer(answer_value)
        return Response(result)


class QuestionnaireRunViewSet(viewsets.ModelViewSet):
    """ViewSet for QuestionnaireRun aggregates"""

    queryset = QuestionnaireRun.objects.all()
    serializer_class = QuestionnaireRunSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['questionnaire_id', 'user_id', 'status']
    search_fields = ['session_token']
    ordering_fields = ['started_at', 'completed_at']
    ordering = ['-started_at']

    @action(detail=True, methods=['post'])
    def submit_answer(self, request, pk=None):
        """Submit an answer for a question"""
        run = self.get_object()
        serializer = AnswerSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            run.submit_answer(
                question_id=serializer.validated_data['question_id'],
                answer_value=serializer.validated_data['answer_value'],
                time_spent=serializer.validated_data.get('time_spent', 0)
            )
            run.save()
            return Response(QuestionnaireRunSerializer(run).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def skip_question(self, request, pk=None):
        """Skip a question"""
        run = self.get_object()
        question_id = request.data.get('question_id')
        if question_id:
            run.skip_question(question_id)
            run.save()
            serializer = self.get_serializer(run)
            return Response(serializer.data)
        return Response({'error': 'question_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete the questionnaire run"""
        run = self.get_object()
        feedback = request.data.get('feedback')
        run.complete_run(feedback)
        run.save()
        serializer = self.get_serializer(run)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def abandon(self, request, pk=None):
        """Abandon the questionnaire run"""
        run = self.get_object()
        run.abandon_run()
        run.save()
        serializer = self.get_serializer(run)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def calculate_score(self, request, pk=None):
        """Calculate the current score"""
        run = self.get_object()
        score_info = run.calculate_score()
        run.save()
        return Response(score_info)

    @action(detail=False, methods=['get'])
    def by_session(self, request):
        """Get a run by session token"""
        session_token = request.query_params.get('token')
        if session_token:
            run = QuestionnaireRun.objects.filter(session_token=session_token).first()
            if run:
                serializer = self.get_serializer(run)
                return Response(serializer.data)
            return Response({'error': 'Run not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'token required'}, status=status.HTTP_400_BAD_REQUEST)
