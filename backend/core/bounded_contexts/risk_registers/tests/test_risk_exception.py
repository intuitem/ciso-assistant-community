"""
Tests for RiskException supporting entity
"""

import uuid
from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone

from core.bounded_contexts.risk_registers.supporting_entities.risk_exception import RiskException
from core.bounded_contexts.risk_registers.domain_events import (
    RiskExceptionRequested,
    RiskExceptionApproved,
)


class RiskExceptionTests(TestCase):
    """Tests for RiskException supporting entity"""
    
    def test_create_exception(self):
        """Test creating a risk exception"""
        exception = RiskException()
        risk_id = uuid.uuid4()
        
        exception.create(
            risk_id=risk_id,
            reason="Temporary exception for testing",
            description="This is a test exception",
            expires_at=timezone.now() + timedelta(days=30)
        )
        exception.save()
        
        self.assertEqual(exception.riskId, risk_id)
        self.assertEqual(exception.lifecycle_state, RiskException.LifecycleState.REQUESTED)
        self.assertIsNotNone(exception.expires_at)
        
        # Check event was raised
        events = exception.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "RiskExceptionRequested")
    
    def test_approve_exception(self):
        """Test approving an exception"""
        exception = RiskException()
        exception.create(risk_id=uuid.uuid4(), reason="Test exception")
        exception.save()
        
        approver_id = uuid.uuid4()
        exception.approve(approver_id)
        exception.save()
        
        self.assertEqual(exception.lifecycle_state, RiskException.LifecycleState.APPROVED)
        self.assertEqual(exception.approved_by_user_id, approver_id)
        self.assertIsNotNone(exception.approved_at)
        
        # Check event was raised
        events = exception.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "RiskExceptionApproved")

