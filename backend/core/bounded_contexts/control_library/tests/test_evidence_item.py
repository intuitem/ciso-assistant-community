"""
Tests for EvidenceItem aggregate
"""

import uuid
from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone

from core.bounded_contexts.control_library.aggregates.evidence_item import EvidenceItem
from core.bounded_contexts.control_library.domain_events import (
    EvidenceCollected,
    EvidenceVerified,
    EvidenceExpired,
)


class EvidenceItemTests(TestCase):
    """Tests for EvidenceItem aggregate"""
    
    def test_create_evidence_item(self):
        """Test creating an evidence item"""
        evidence = EvidenceItem()
        evidence.create(
            name="Security Scan Report",
            description="Quarterly security scan results",
            source_type="upload",
            uri="https://example.com/report.pdf"
        )
        evidence.save()
        
        self.assertEqual(evidence.name, "Security Scan Report")
        self.assertEqual(evidence.lifecycle_state, EvidenceItem.LifecycleState.COLLECTED)
        self.assertEqual(evidence.source_type, "upload")
        
        # Check event was raised
        events = evidence.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "EvidenceCollected")
    
    def test_verify_evidence(self):
        """Test verifying evidence"""
        evidence = EvidenceItem()
        evidence.create(name="Security Scan Report")
        evidence.save()
        
        evidence.verify()
        evidence.save()
        
        self.assertEqual(evidence.lifecycle_state, EvidenceItem.LifecycleState.VERIFIED)
        
        # Check event was raised
        events = evidence.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "EvidenceVerified")
    
    def test_expire_evidence(self):
        """Test expiring evidence"""
        evidence = EvidenceItem()
        evidence.create(name="Security Scan Report")
        evidence.save()
        
        evidence.expire()
        evidence.save()
        
        self.assertEqual(evidence.lifecycle_state, EvidenceItem.LifecycleState.EXPIRED)
        
        # Check event was raised
        events = evidence.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "EvidenceExpired")
    
    def test_is_expired(self):
        """Test checking if evidence is expired"""
        evidence = EvidenceItem()
        evidence.create(
            name="Security Scan Report",
            expires_at=timezone.now() - timedelta(days=1)
        )
        evidence.save()
        
        self.assertTrue(evidence.is_expired())

