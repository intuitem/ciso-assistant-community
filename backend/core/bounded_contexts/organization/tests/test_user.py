"""
Tests for User aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.organization.aggregates.user import User
from core.bounded_contexts.organization.domain_events import (
    UserCreated,
    UserActivated,
    UserAssignedToGroup,
)


class UserTests(TestCase):
    """Tests for User aggregate"""
    
    def test_create_user(self):
        """Test creating a user"""
        user = User()
        user.create(
            email="test@example.com",
            display_name="Test User",
            password="password123"
        )
        user.save()
        
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.display_name, "Test User")
        self.assertEqual(user.lifecycle_state, User.LifecycleState.INVITED)
        self.assertIsNotNone(user.password)
        
        # Check event was raised
        events = user.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "UserCreated")
    
    def test_activate_user(self):
        """Test activating a user"""
        user = User()
        user.create(email="test@example.com")
        user.save()
        
        user.activate()
        user.save()
        
        self.assertEqual(user.lifecycle_state, User.LifecycleState.ACTIVE)
        
        # Check event was raised
        events = user.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "UserActivated")
    
    def test_assign_to_group(self):
        """Test assigning user to a group"""
        user = User()
        user.create(email="test@example.com")
        user.save()
        
        group_id = uuid.uuid4()
        user.assign_to_group(group_id)
        user.save()
        
        self.assertIn(group_id, user.groupIds)
        
        # Check event was raised
        events = user.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "UserAssignedToGroup")
    
    def test_assign_to_org_unit(self):
        """Test assigning user to an organizational unit"""
        user = User()
        user.create(email="test@example.com")
        user.save()
        
        org_unit_id = uuid.uuid4()
        user.assign_to_org_unit(org_unit_id)
        user.save()
        
        self.assertIn(org_unit_id, user.orgUnitIds)
        
        # Check event was raised
        events = user.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "UserAssignedToOrgUnit")

