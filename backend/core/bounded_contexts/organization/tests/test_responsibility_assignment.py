"""
Tests for ResponsibilityAssignment association
"""

import uuid
from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError

from core.bounded_contexts.organization.associations.responsibility_assignment import ResponsibilityAssignment
from core.bounded_contexts.organization.domain_events import (
    ResponsibilityAssigned,
    ResponsibilityRevoked,
)


class ResponsibilityAssignmentTests(TestCase):
    """Tests for ResponsibilityAssignment association"""
    
    def test_create_assignment(self):
        """Test creating a responsibility assignment"""
        assignment = ResponsibilityAssignment()
        subject_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        assignment.assign(
            subject_type="asset",
            subject_id=subject_id,
            user_id=user_id,
            role="owner",
            start_date=date.today()
        )
        assignment.save()
        
        self.assertEqual(assignment.subject_type, "asset")
        self.assertEqual(assignment.subject_id, subject_id)
        self.assertEqual(assignment.userId, user_id)
        self.assertEqual(assignment.role, "owner")
        
        # Check event was raised
        events = assignment.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ResponsibilityAssigned")
    
    def test_revoke_assignment(self):
        """Test revoking a responsibility assignment"""
        assignment = ResponsibilityAssignment()
        assignment.assign(
            subject_type="asset",
            subject_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            role="owner"
        )
        assignment.save()
        
        assignment.revoke()
        assignment.save()
        
        self.assertIsNotNone(assignment.end_date)
        
        # Check event was raised
        events = assignment.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ResponsibilityRevoked")
    
    def test_is_active(self):
        """Test checking if assignment is active"""
        assignment = ResponsibilityAssignment()
        assignment.assign(
            subject_type="asset",
            subject_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            role="owner",
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1)
        )
        assignment.save()
        
        self.assertTrue(assignment.is_active())
        
        # Test expired assignment
        assignment.end_date = date.today() - timedelta(days=1)
        assignment.save()
        self.assertFalse(assignment.is_active())
    
    def test_validate_end_date_after_start_date(self):
        """Test that end date must be after start date"""
        assignment = ResponsibilityAssignment()
        assignment.subject_type = "asset"
        assignment.subject_id = uuid.uuid4()
        assignment.userId = uuid.uuid4()
        assignment.role = "owner"
        assignment.start_date = date.today()
        assignment.end_date = date.today() - timedelta(days=1)
        
        with self.assertRaises(ValidationError):
            assignment.clean()

