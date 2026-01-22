"""
Questionnaire Service

Service for managing questionnaire execution, dynamic question flows,
conditional logic evaluation, and scoring calculations.
"""

import uuid
from typing import Dict, List, Any, Optional, Tuple
from django.utils import timezone

from ..models.questionnaire import Questionnaire
from ..models.question import Question
from ..models.questionnaire_run import QuestionnaireRun


class QuestionnaireService:
    """
    Service for questionnaire execution and management.

    Handles dynamic question flows, conditional logic evaluation,
    scoring calculations, and progress management.
    """

    def __init__(self):
        """Initialize questionnaire service"""
        pass

    def start_questionnaire_run(
        self,
        questionnaire_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        session_token: Optional[str] = None
    ) -> QuestionnaireRun:
        """
        Start a new questionnaire run.

        Args:
            questionnaire_id: ID of the questionnaire to start
            user_id: ID of the user (None for anonymous)
            session_token: Session token for anonymous users

        Returns:
            New QuestionnaireRun instance
        """
        # Get questionnaire
        questionnaire = self._get_questionnaire(questionnaire_id)
        if not questionnaire or questionnaire.status != 'published':
            raise ValueError("Questionnaire not found or not published")

        # Create run
        run = QuestionnaireRun()
        run.start_run(
            questionnaire_id=questionnaire_id,
            user_id=user_id,
            session_token=session_token,
            enable_scoring=questionnaire.enable_scoring,
            expires_at=self._calculate_expiry(questionnaire)
        )

        # Initialize question flow
        visible_questions = self._calculate_visible_questions(questionnaire, run)
        run.update_progress(0, visible_questions)

        return run

    def get_next_question(self, run_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get the next question for a questionnaire run.

        Args:
            run_id: ID of the questionnaire run

        Returns:
            Question data or None if completed
        """
        run = self._get_run(run_id)
        if not run or not run.is_in_progress:
            return None

        questionnaire = self._get_questionnaire(run.questionnaire_id)
        if not questionnaire:
            return None

        # Find next visible question
        visible_questions = run.visible_question_ids
        current_index = run.current_question_index

        if current_index >= len(visible_questions):
            # Questionnaire completed
            return None

        question_id = visible_questions[current_index]
        question = self._get_question(question_id)

        if not question:
            return None

        return {
            'question_id': str(question.id),
            'question': self._format_question_data(question),
            'progress': {
                'current': current_index + 1,
                'total': len(visible_questions),
                'percentage': run.get_progress_percentage()
            },
            'can_go_back': questionnaire.allow_back_navigation and current_index > 0
        }

    def submit_answer(
        self,
        run_id: uuid.UUID,
        question_id: str,
        answer_value: Any,
        time_spent: int = 0
    ) -> Dict[str, Any]:
        """
        Submit an answer for a question.

        Args:
            run_id: ID of the questionnaire run
            question_id: ID of the question
            answer_value: The answer value
            time_spent: Time spent on question in seconds

        Returns:
            Result of answer submission
        """
        run = self._get_run(run_id)
        questionnaire = self._get_questionnaire(run.questionnaire_id)
        question = self._get_question(question_id)

        if not all([run, questionnaire, question]):
            raise ValueError("Invalid run, questionnaire, or question")

        # Validate answer
        validation = question.validate_answer(answer_value)
        if not validation['valid']:
            return {
                'success': False,
                'errors': validation['errors'],
                'warnings': validation['warnings']
            }

        # Submit answer
        run.submit_answer(question_id, answer_value, time_spent)

        # Calculate score if enabled
        score_data = None
        if questionnaire.enable_scoring:
            score_data = question.calculate_score(answer_value)
            run.current_score += score_data

        # Update visible questions based on conditional logic
        visible_questions = self._calculate_visible_questions(questionnaire, run)
        run.update_progress(run.current_question_index + 1, visible_questions)

        # Check if questionnaire is completed
        is_completed = run.current_question_index >= len(visible_questions)

        if is_completed:
            run.complete_run()
            final_score = run.calculate_score() if questionnaire.enable_scoring else None
        else:
            final_score = None

        return {
            'success': True,
            'validation': validation,
            'score_awarded': score_data,
            'current_score': run.current_score,
            'is_completed': is_completed,
            'final_score': final_score,
            'next_question': self.get_next_question(run_id) if not is_completed else None
        }

    def go_to_previous_question(self, run_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Navigate to the previous question.

        Args:
            run_id: ID of the questionnaire run

        Returns:
            Previous question data or None
        """
        run = self._get_run(run_id)
        questionnaire = self._get_questionnaire(run.questionnaire_id)

        if not run or not questionnaire or not questionnaire.allow_back_navigation:
            return None

        if run.current_question_index > 0:
            run.current_question_index -= 1
            return self.get_next_question(run_id)

        return None

    def skip_question(self, run_id: uuid.UUID, question_id: str) -> bool:
        """
        Skip a question without answering.

        Args:
            run_id: ID of the questionnaire run
            question_id: ID of the question to skip

        Returns:
            True if successfully skipped
        """
        run = self._get_run(run_id)
        if not run:
            return False

        run.skip_question(question_id)

        # Update progress
        questionnaire = self._get_questionnaire(run.questionnaire_id)
        if questionnaire:
            visible_questions = self._calculate_visible_questions(questionnaire, run)
            run.update_progress(run.current_question_index, visible_questions)

        return True

    def get_questionnaire_progress(self, run_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get detailed progress information for a questionnaire run.

        Args:
            run_id: ID of the questionnaire run

        Returns:
            Progress information
        """
        run = self._get_run(run_id)
        if not run:
            return {'error': 'Run not found'}

        questionnaire = self._get_questionnaire(run.questionnaire_id)
        if not questionnaire:
            return {'error': 'Questionnaire not found'}

        return {
            'run_id': str(run.id),
            'status': run.status,
            'progress_percentage': run.get_progress_percentage(),
            'current_question': run.current_question_index + 1,
            'total_questions': run.total_questions,
            'questions_answered': run.questions_answered,
            'questions_skipped': len(run.skipped_question_ids),
            'time_spent_seconds': run.time_spent_seconds,
            'started_at': run.started_at.isoformat() if run.started_at else None,
            'estimated_completion_time': self._estimate_completion_time(questionnaire, run),
            'can_navigate_back': questionnaire.allow_back_navigation,
            'scoring_enabled': run.enable_scoring,
            'current_score': run.current_score if run.enable_scoring else None
        }

    def get_questionnaire_results(self, run_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get complete results for a finished questionnaire run.

        Args:
            run_id: ID of the questionnaire run

        Returns:
            Complete results including answers and scoring
        """
        run = self._get_run(run_id)
        if not run or not run.is_completed:
            return {'error': 'Run not completed or not found'}

        questionnaire = self._get_questionnaire(run.questionnaire_id)
        if not questionnaire:
            return {'error': 'Questionnaire not found'}

        # Format answers with question details
        formatted_answers = []
        for question_id, answer_data in run.answers.items():
            question = self._get_question(question_id)
            if question:
                formatted_answers.append({
                    'question_id': question_id,
                    'question_text': question.text,
                    'question_type': question.question_type,
                    'answer': answer_data['value'],
                    'timestamp': answer_data['timestamp'],
                    'time_spent_seconds': answer_data.get('time_spent_seconds', 0)
                })

        results = {
            'run_id': str(run.id),
            'questionnaire_title': questionnaire.title,
            'status': run.status,
            'started_at': run.started_at.isoformat() if run.started_at else None,
            'completed_at': run.completed_at.isoformat() if run.completed_at else None,
            'total_time_seconds': run.duration_seconds,
            'answers': formatted_answers,
            'questions_answered': len(formatted_answers),
            'questions_skipped': len(run.skipped_question_ids),
            'feedback': run.feedback
        }

        # Add scoring if enabled
        if run.enable_scoring:
            results.update({
                'scoring_enabled': True,
                'final_score': run.current_score,
                'max_possible_score': run.max_possible_score,
                'score_percentage': run.final_score_percentage,
                'passed': run.passed,
                'passing_score': run.passing_score
            })

        return results

    def _calculate_visible_questions(self, questionnaire: Questionnaire, run: QuestionnaireRun) -> List[str]:
        """
        Calculate which questions should be visible based on conditional logic.

        Args:
            questionnaire: The questionnaire
            run: The current run state

        Returns:
            List of visible question IDs in order
        """
        visible_questions = []

        for question_id in questionnaire.question_ids:
            question = self._get_question(question_id)
            if not question:
                continue

            # Check conditional logic
            if self._evaluate_conditional_logic(question, run):
                visible_questions.append(question_id)

        return visible_questions

    def _evaluate_conditional_logic(self, question: Question, run: QuestionnaireRun) -> bool:
        """
        Evaluate conditional logic for a question.

        Args:
            question: The question to evaluate
            run: The current run state

        Returns:
            True if question should be shown
        """
        if not question.conditional_logic:
            return True

        logic = question.conditional_logic
        show_if = logic.get('show_if')

        if not show_if:
            return True

        # Evaluate condition
        condition_question_id = show_if.get('question_id')
        operator = show_if.get('operator', 'equals')
        expected_value = show_if.get('value')

        if not condition_question_id:
            return True

        # Get the answer for the condition question
        condition_answer = run.get_answer(condition_question_id)
        if not condition_answer:
            return False

        actual_value = condition_answer['value']

        # Evaluate based on operator
        if operator == 'equals':
            return actual_value == expected_value
        elif operator == 'not_equals':
            return actual_value != expected_value
        elif operator == 'contains':
            return expected_value in str(actual_value)
        elif operator == 'greater_than':
            try:
                return float(actual_value) > float(expected_value)
            except (ValueError, TypeError):
                return False
        elif operator == 'less_than':
            try:
                return float(actual_value) < float(expected_value)
            except (ValueError, TypeError):
                return False

        return True

    def _calculate_expiry(self, questionnaire: Questionnaire) -> Optional[timezone.datetime]:
        """Calculate when a questionnaire run should expire"""
        if questionnaire.estimated_duration_minutes:
            return timezone.now() + timezone.timedelta(minutes=questionnaire.estimated_duration_minutes * 2)  # 2x buffer
        return None

    def _estimate_completion_time(self, questionnaire: Questionnaire, run: QuestionnaireRun) -> Optional[int]:
        """Estimate remaining completion time in minutes"""
        if not questionnaire.estimated_duration_minutes or run.total_questions == 0:
            return None

        questions_remaining = run.total_questions - run.questions_answered
        avg_time_per_question = questionnaire.estimated_duration_minutes / run.total_questions

        return int(questions_remaining * avg_time_per_question)

    def _get_questionnaire(self, questionnaire_id: uuid.UUID) -> Optional[Questionnaire]:
        """Get questionnaire by ID"""
        try:
            return Questionnaire.objects.get(id=questionnaire_id, is_active=True)
        except Questionnaire.DoesNotExist:
            return None

    def _get_question(self, question_id: str) -> Optional[Question]:
        """Get question by ID"""
        try:
            return Question.objects.get(id=question_id, is_active=True)
        except Question.DoesNotExist:
            return None

    def _get_run(self, run_id: uuid.UUID) -> Optional[QuestionnaireRun]:
        """Get questionnaire run by ID"""
        try:
            return QuestionnaireRun.objects.get(id=run_id)
        except QuestionnaireRun.DoesNotExist:
            return None

    def _format_question_data(self, question: Question) -> Dict[str, Any]:
        """Format question data for API response"""
        return {
            'id': str(question.id),
            'text': question.text,
            'help_text': question.help_text,
            'type': question.question_type,
            'options': question.options,
            'is_required': question.is_required,
            'validation_rules': question.validation_rules,
            'enable_scoring': question.enable_scoring,
            'points': question.points if question.enable_scoring else 0
        }
