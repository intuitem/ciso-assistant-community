"""
Tests for ComplianceFinding association
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.compliance.associations.compliance_finding import ComplianceFinding
from core.bounded_contexts.compliance.domain_events import (
    ComplianceFindingCreated,
    ComplianceFindingStatusChanged,
)


class ComplianceFindingTests(TestCase):
    """Tests for ComplianceFinding association"""
    
    def test_create_finding(self):
        """Test creating a compliance finding"""
        finding = ComplianceFinding()
        audit_id = uuid.uuid4()
        
        finding.create(
            title="Missing Access Control Policy",
            source_type="audit",
            source_id=audit_id,
            description="Access control policy not documented",
            severity="high"
        )
        finding.save()
        
        self.assertEqual(finding.title, "Missing Access Control Policy")
        self.assertEqual(finding.source_type, "audit")
        self.assertEqual(finding.severity, "high")
        self.assertEqual(finding.lifecycle_state, ComplianceFinding.LifecycleState.OPEN)
        
        # Check event was raised
        events = finding.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ComplianceFindingCreated")
    
    def test_triage_finding(self):
        """Test triaging a finding"""
        finding = ComplianceFinding()
        finding.create(title="Test Finding", source_type="audit", source_id=uuid.uuid4())
        finding.save()
        
        finding.triage()
        finding.save()
        
        self.assertEqual(finding.lifecycle_state, ComplianceFinding.LifecycleState.TRIAGED)
        
        # Check event was raised
        events = finding.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ComplianceFindingStatusChanged")
    
    def test_start_remediation(self):
        """Test starting remediation"""
        finding = ComplianceFinding()
        finding.create(title="Test Finding", source_type="audit", source_id=uuid.uuid4())
        finding.save()
        finding.triage()
        finding.save()
        
        finding.start_remediation()
        finding.save()
        
        self.assertEqual(finding.lifecycle_state, ComplianceFinding.LifecycleState.REMEDIATING)

