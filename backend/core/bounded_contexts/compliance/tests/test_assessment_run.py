"""
Tests for AssessmentRun association
"""

import uuid
from django.test import TestCase
from django.utils import timezone

from core.bounded_contexts.compliance.associations.assessment_run import AssessmentRun
from core.bounded_contexts.compliance.domain_events import (
    AssessmentRunInvited,
    AssessmentRunStarted,
    AssessmentRunSubmitted,
)


class AssessmentRunTests(TestCase):
    """Tests for AssessmentRun association"""
    
    def test_create_assessment_run(self):
        """Test creating an assessment run"""
        run = AssessmentRun()
        assessment_id = uuid.uuid4()
        asset_id = uuid.uuid4()
        
        run.create(
            assessment_id=assessment_id,
            target_type="asset",
            target_id=asset_id,
            invited_user_ids=[uuid.uuid4()]
        )
        run.save()
        
        self.assertEqual(run.assessmentId, assessment_id)
        self.assertEqual(run.target_type, "asset")
        self.assertEqual(run.target_id, asset_id)
        self.assertEqual(run.lifecycle_state, AssessmentRun.LifecycleState.INVITED)
        
        # Check event was raised
        events = run.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "AssessmentRunInvited")
    
    def test_start_assessment_run(self):
        """Test starting an assessment run"""
        run = AssessmentRun()
        run.create(assessment_id=uuid.uuid4(), target_type="asset", target_id=uuid.uuid4())
        run.save()
        
        respondent_id = uuid.uuid4()
        run.start(respondent_id)
        run.save()
        
        self.assertEqual(run.lifecycle_state, AssessmentRun.LifecycleState.IN_PROGRESS)
        self.assertIn(respondent_id, run.respondentUserIds)
        self.assertIsNotNone(run.started_at)
        
        # Check event was raised
        events = run.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "AssessmentRunStarted")
    
    def test_submit_assessment_run(self):
        """Test submitting an assessment run"""
        run = AssessmentRun()
        run.create(assessment_id=uuid.uuid4(), target_type="asset", target_id=uuid.uuid4())
        run.save()
        run.start(uuid.uuid4())
        run.save()
        
        answers = [
            {"questionId": "q1", "value": "Yes", "notes": None},
            {"questionId": "q2", "value": "No", "notes": "Not applicable"},
        ]
        run.submit(answers=answers, score=85.5)
        run.save()
        
        self.assertEqual(run.lifecycle_state, AssessmentRun.LifecycleState.SUBMITTED)
        self.assertEqual(len(run.answers), 2)
        self.assertEqual(run.score, 85.5)
        self.assertIsNotNone(run.submitted_at)
        
        # Check event was raised
        events = run.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "AssessmentRunSubmitted")
    
    def test_add_answer(self):
        """Test adding an answer"""
        run = AssessmentRun()
        run.create(assessment_id=uuid.uuid4(), target_type="asset", target_id=uuid.uuid4())
        run.save()
        
        run.add_answer("q1", "Yes", "This is the answer")
        run.save()
        
        self.assertEqual(len(run.answers), 1)
        self.assertEqual(run.answers[0]["questionId"], "q1")
        self.assertEqual(run.answers[0]["value"], "Yes")

