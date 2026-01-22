"""
Tests for Policy aggregate
"""

import uuid
from datetime import date
from django.test import TestCase

from core.bounded_contexts.control_library.aggregates.policy import Policy
from core.bounded_contexts.control_library.domain_events import (
    PolicyCreated,
    PolicyPublished,
    PolicyRetired,
)


class PolicyTests(TestCase):
    """Tests for Policy aggregate"""
    
    def test_create_policy(self):
        """Test creating a policy"""
        policy = Policy()
        policy.create(
            title="Password Policy",
            version="1.0",
            description="Policy for password management"
        )
        policy.save()
        
        self.assertEqual(policy.title, "Password Policy")
        self.assertEqual(policy.version, "1.0")
        self.assertEqual(policy.lifecycle_state, Policy.LifecycleState.DRAFT)
        
        # Check event was raised
        events = policy.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "PolicyCreated")
    
    def test_publish_policy(self):
        """Test publishing a policy"""
        policy = Policy()
        policy.create(title="Password Policy", version="1.0")
        policy.save()
        
        policy.publish()
        policy.save()
        
        self.assertEqual(policy.lifecycle_state, Policy.LifecycleState.PUBLISHED)
        self.assertIsNotNone(policy.publication_date)
        
        # Check event was raised
        events = policy.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "PolicyPublished")
    
    def test_retire_policy(self):
        """Test retiring a policy"""
        policy = Policy()
        policy.create(title="Password Policy", version="1.0")
        policy.save()
        policy.publish()
        policy.save()
        
        policy.retire()
        policy.save()
        
        self.assertEqual(policy.lifecycle_state, Policy.LifecycleState.RETIRED)
        
        # Check event was raised
        events = policy.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "PolicyRetired")
    
    def test_assign_owner(self):
        """Test assigning an owner to a policy"""
        policy = Policy()
        policy.create(title="Password Policy")
        policy.save()
        
        owner_id = uuid.uuid4()
        policy.assign_owner(owner_id)
        policy.save()
        
        self.assertIn(owner_id, policy.ownerUserIds)

