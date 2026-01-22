"""
Tests for PolicyAcknowledgement association
"""

import uuid
from datetime import datetime
from django.test import TestCase
from django.utils import timezone

from core.bounded_contexts.control_library.associations.policy_acknowledgement import PolicyAcknowledgement
from core.bounded_contexts.control_library.domain_events import (
    PolicyAcknowledged,
)


class PolicyAcknowledgementTests(TestCase):
    """Tests for PolicyAcknowledgement association"""
    
    def test_acknowledge_policy(self):
        """Test acknowledging a policy"""
        acknowledgement = PolicyAcknowledgement()
        policy_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        acknowledgement.acknowledge(
            policy_id=policy_id,
            policy_version="1.0",
            user_id=user_id,
            method="clickwrap"
        )
        acknowledgement.save()
        
        self.assertEqual(acknowledgement.policyId, policy_id)
        self.assertEqual(acknowledgement.policy_version, "1.0")
        self.assertEqual(acknowledgement.userId, user_id)
        self.assertEqual(acknowledgement.method, "clickwrap")
        self.assertIsNotNone(acknowledgement.acknowledged_at)
        
        # Check event was raised
        events = acknowledgement.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "PolicyAcknowledged")

