"""
Tests for ThirdPartyRisk aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.risk_registers.aggregates.third_party_risk import ThirdPartyRisk
from core.bounded_contexts.risk_registers.domain_events import (
    ThirdPartyRiskCreated,
    ThirdPartyRiskAssessed,
    ThirdPartyRiskTreated,
)


class ThirdPartyRiskTests(TestCase):
    """Tests for ThirdPartyRisk aggregate"""
    
    def test_create_third_party_risk(self):
        """Test creating a third party risk"""
        risk = ThirdPartyRisk()
        risk.create(
            title="Vendor Data Breach Risk",
            description="Risk of vendor exposing sensitive data"
        )
        risk.save()
        
        self.assertEqual(risk.title, "Vendor Data Breach Risk")
        self.assertEqual(risk.lifecycle_state, ThirdPartyRisk.LifecycleState.DRAFT)
        
        # Check event was raised
        events = risk.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ThirdPartyRiskCreated")
    
    def test_assess_risk(self):
        """Test assessing a third party risk"""
        risk = ThirdPartyRisk()
        risk.create(title="Vendor Risk")
        risk.save()
        
        risk.assess(
            likelihood=3,
            impact=4,
            inherent_score=12,
            residual_score=8,
            rationale="Medium likelihood, high impact"
        )
        risk.save()
        
        self.assertEqual(risk.lifecycle_state, ThirdPartyRisk.LifecycleState.ASSESSED)
        self.assertEqual(risk.scoring["likelihood"], 3)
        self.assertEqual(risk.scoring["residual_score"], 8)
        
        # Check event was raised
        events = risk.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ThirdPartyRiskAssessed")
    
    def test_treat_risk(self):
        """Test treating a third party risk"""
        risk = ThirdPartyRisk()
        risk.create(title="Vendor Risk")
        risk.save()
        risk.assess(3, 4, 12, 8)
        risk.save()
        
        risk.treat()
        risk.save()
        
        self.assertEqual(risk.lifecycle_state, ThirdPartyRisk.LifecycleState.TREATED)
        
        # Check event was raised
        events = risk.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ThirdPartyRiskTreated")
    
    def test_add_third_party(self):
        """Test adding a third party to a risk"""
        risk = ThirdPartyRisk()
        risk.create(title="Vendor Risk")
        risk.save()
        
        third_party_id = uuid.uuid4()
        risk.add_third_party(third_party_id)
        risk.save()
        
        self.assertIn(third_party_id, risk.thirdPartyIds)
    
    def test_add_service(self):
        """Test adding a service to a risk"""
        risk = ThirdPartyRisk()
        risk.create(title="Vendor Risk")
        risk.save()
        
        service_id = uuid.uuid4()
        risk.add_service(service_id)
        risk.save()
        
        self.assertIn(service_id, risk.serviceIds)

