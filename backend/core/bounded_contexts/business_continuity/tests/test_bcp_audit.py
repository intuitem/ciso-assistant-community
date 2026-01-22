"""
Tests for BcpAudit supporting entity
"""

import uuid
from datetime import datetime
from django.test import TestCase
from django.utils import timezone

from core.bounded_contexts.business_continuity.supporting_entities.bcp_audit import BcpAudit
from core.bounded_contexts.business_continuity.domain_events import (
    BcpAuditCreated,
    BcpAuditCompleted,
)


class BcpAuditTests(TestCase):
    """Tests for BcpAudit supporting entity"""
    
    def test_create_audit(self):
        """Test creating a BCP audit"""
        audit = BcpAudit()
        bcp_id = uuid.uuid4()
        
        audit.create(
            bcp_id=bcp_id,
            name="Q1 2024 BCP Review",
            description="Quarterly review of business continuity plan"
        )
        audit.save()
        
        self.assertEqual(audit.bcpId, bcp_id)
        self.assertEqual(audit.name, "Q1 2024 BCP Review")
        self.assertEqual(audit.lifecycle_state, BcpAudit.LifecycleState.PLANNED)
        
        # Check event was raised
        events = audit.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "BcpAuditCreated")
    
    def test_complete_audit(self):
        """Test completing an audit"""
        audit = BcpAudit()
        audit.create(bcp_id=uuid.uuid4(), name="Q1 2024 BCP Review")
        audit.save()
        audit.start(timezone.now())
        audit.save()
        
        audit.complete("pass", "All tests passed")
        audit.save()
        
        self.assertEqual(audit.lifecycle_state, BcpAudit.LifecycleState.REPORTED)
        self.assertEqual(audit.outcome, "pass")
        
        # Check event was raised
        events = audit.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "BcpAuditCompleted")

