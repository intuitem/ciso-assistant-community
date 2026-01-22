"""
Tests for BusinessRisk aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.risk_registers.aggregates.business_risk import BusinessRisk
from core.bounded_contexts.risk_registers.domain_events import (
    BusinessRiskCreated,
    BusinessRiskAssessed,
    BusinessRiskAccepted,
)


class BusinessRiskTests(TestCase):
    """Tests for BusinessRisk aggregate"""
    
    def test_create_business_risk(self):
        """Test creating a business risk"""
        risk = BusinessRisk()
        risk.create(
            title="Process Failure Risk",
            description="Risk of critical business process failure"
        )
        risk.save()
        
        self.assertEqual(risk.title, "Process Failure Risk")
        self.assertEqual(risk.lifecycle_state, BusinessRisk.LifecycleState.DRAFT)
        
        # Check event was raised
        events = risk.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "BusinessRiskCreated")
    
    def test_assess_risk(self):
        """Test assessing a business risk"""
        risk = BusinessRisk()
        risk.create(title="Process Risk")
        risk.save()
        
        risk.assess(
            likelihood=2,
            impact=5,
            inherent_score=10,
            residual_score=6,
            rationale="Low likelihood, critical impact"
        )
        risk.save()
        
        self.assertEqual(risk.lifecycle_state, BusinessRisk.LifecycleState.ASSESSED)
        self.assertEqual(risk.scoring["impact"], 5)
        
        # Check event was raised
        events = risk.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "BusinessRiskAssessed")
    
    def test_accept_risk(self):
        """Test accepting a business risk"""
        risk = BusinessRisk()
        risk.create(title="Process Risk")
        risk.save()
        risk.assess(2, 5, 10, 6)
        risk.save()
        
        risk.accept()
        risk.save()
        
        self.assertEqual(risk.lifecycle_state, BusinessRisk.LifecycleState.ACCEPTED)
        
        # Check event was raised
        events = risk.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "BusinessRiskAccepted")
    
    def test_add_process(self):
        """Test adding a process to a risk"""
        risk = BusinessRisk()
        risk.create(title="Process Risk")
        risk.save()
        
        process_id = uuid.uuid4()
        risk.add_process(process_id)
        risk.save()
        
        self.assertIn(process_id, risk.processIds)
    
    def test_add_org_unit(self):
        """Test adding an organizational unit to a risk"""
        risk = BusinessRisk()
        risk.create(title="Process Risk")
        risk.save()
        
        org_unit_id = uuid.uuid4()
        risk.add_org_unit(org_unit_id)
        risk.save()
        
        self.assertIn(org_unit_id, risk.orgUnitIds)

