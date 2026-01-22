"""
Tests for RiskTreatmentPlan supporting entity
"""

import uuid
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone

from core.bounded_contexts.risk_registers.supporting_entities.risk_treatment_plan import RiskTreatmentPlan
from core.bounded_contexts.risk_registers.domain_events import (
    RiskTreatmentPlanCreated,
    RiskTreatmentPlanActivated,
    RiskTreatmentPlanCompleted,
)


class RiskTreatmentPlanTests(TestCase):
    """Tests for RiskTreatmentPlan supporting entity"""
    
    def test_create_treatment_plan(self):
        """Test creating a risk treatment plan"""
        plan = RiskTreatmentPlan()
        risk_id = uuid.uuid4()
        
        plan.create(
            risk_id=risk_id,
            name="Data Encryption Plan",
            strategy="mitigate",
            description="Implement encryption for sensitive data"
        )
        plan.save()
        
        self.assertEqual(plan.riskId, risk_id)
        self.assertEqual(plan.name, "Data Encryption Plan")
        self.assertEqual(plan.strategy, "mitigate")
        self.assertEqual(plan.lifecycle_state, RiskTreatmentPlan.LifecycleState.DRAFT)
        
        # Check event was raised
        events = plan.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "RiskTreatmentPlanCreated")
    
    def test_activate_plan(self):
        """Test activating a treatment plan"""
        plan = RiskTreatmentPlan()
        plan.create(risk_id=uuid.uuid4(), name="Test Plan", strategy="mitigate")
        plan.save()
        
        plan.activate()
        plan.save()
        
        self.assertEqual(plan.lifecycle_state, RiskTreatmentPlan.LifecycleState.ACTIVE)
        self.assertIsNotNone(plan.started_at)
        
        # Check event was raised
        events = plan.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "RiskTreatmentPlanActivated")
    
    def test_complete_plan(self):
        """Test completing a treatment plan"""
        plan = RiskTreatmentPlan()
        plan.create(risk_id=uuid.uuid4(), name="Test Plan", strategy="mitigate")
        plan.save()
        plan.activate()
        plan.save()
        
        plan.complete()
        plan.save()
        
        self.assertEqual(plan.lifecycle_state, RiskTreatmentPlan.LifecycleState.COMPLETED)
        self.assertIsNotNone(plan.completed_at)
        
        # Check event was raised
        events = plan.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "RiskTreatmentPlanCompleted")
    
    def test_add_task(self):
        """Test adding a task to a treatment plan"""
        plan = RiskTreatmentPlan()
        plan.create(risk_id=uuid.uuid4(), name="Test Plan", strategy="mitigate")
        plan.save()
        
        owner_id = uuid.uuid4()
        due_date = date.today() + timedelta(days=30)
        plan.add_task(
            title="Implement encryption",
            owner_user_id=owner_id,
            due_date=due_date,
            status="Open"
        )
        plan.save()
        
        self.assertEqual(len(plan.tasks), 1)
        self.assertEqual(plan.tasks[0]["title"], "Implement encryption")
        self.assertEqual(plan.tasks[0]["ownerUserId"], str(owner_id))
        self.assertEqual(plan.tasks[0]["status"], "Open")
    
    def test_update_task_status(self):
        """Test updating a task's status"""
        plan = RiskTreatmentPlan()
        plan.create(risk_id=uuid.uuid4(), name="Test Plan", strategy="mitigate")
        plan.save()
        
        owner_id = uuid.uuid4()
        plan.add_task("Task 1", owner_id, status="Open")
        plan.save()
        
        task_id = plan.tasks[0]["id"]
        plan.update_task_status(task_id, "InProgress")
        plan.save()
        
        self.assertEqual(plan.tasks[0]["status"], "InProgress")

