"""
Tests for AssetRisk aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.risk_registers.aggregates.asset_risk import AssetRisk
from core.bounded_contexts.risk_registers.domain_events import (
    AssetRiskCreated,
    AssetRiskAssessed,
    AssetRiskTreated,
)


class AssetRiskTests(TestCase):
    """Tests for AssetRisk aggregate"""
    
    def test_create_asset_risk(self):
        """Test creating an asset risk"""
        risk = AssetRisk()
        risk.create(
            title="Data Breach Risk",
            description="Risk of unauthorized access to sensitive data",
            threat="Malicious actors",
            vulnerability="Weak access controls"
        )
        risk.save()
        
        self.assertEqual(risk.title, "Data Breach Risk")
        self.assertEqual(risk.lifecycle_state, AssetRisk.LifecycleState.DRAFT)
        self.assertEqual(risk.threat, "Malicious actors")
        
        # Check event was raised
        events = risk.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "AssetRiskCreated")
    
    def test_assess_risk(self):
        """Test assessing a risk"""
        risk = AssetRisk()
        risk.create(title="Data Breach Risk")
        risk.save()
        
        risk.assess(
            likelihood=4,
            impact=5,
            inherent_score=20,
            residual_score=10,
            rationale="High likelihood, critical impact"
        )
        risk.save()
        
        self.assertEqual(risk.lifecycle_state, AssetRisk.LifecycleState.ASSESSED)
        self.assertEqual(risk.scoring["likelihood"], 4)
        self.assertEqual(risk.scoring["impact"], 5)
        self.assertEqual(risk.scoring["inherent_score"], 20)
        
        # Check event was raised
        events = risk.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "AssetRiskAssessed")
    
    def test_treat_risk(self):
        """Test treating a risk"""
        risk = AssetRisk()
        risk.create(title="Data Breach Risk")
        risk.save()
        risk.assess(3, 4, 12, 8)
        risk.save()
        
        treatment_plan_id = uuid.uuid4()
        risk.treat(treatment_plan_id)
        risk.save()
        
        self.assertEqual(risk.lifecycle_state, AssetRisk.LifecycleState.TREATED)
        self.assertEqual(risk.treatmentPlanId, treatment_plan_id)
        
        # Check event was raised
        events = risk.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "AssetRiskTreated")
    
    def test_add_asset(self):
        """Test adding an asset to a risk"""
        risk = AssetRisk()
        risk.create(title="Data Breach Risk")
        risk.save()
        
        asset_id = uuid.uuid4()
        risk.add_asset(asset_id)
        risk.save()
        
        self.assertIn(asset_id, risk.assetIds)

