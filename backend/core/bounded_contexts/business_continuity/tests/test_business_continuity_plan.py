"""
Tests for BusinessContinuityPlan aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.business_continuity.aggregates.business_continuity_plan import BusinessContinuityPlan
from core.bounded_contexts.business_continuity.domain_events import (
    BusinessContinuityPlanCreated,
    BusinessContinuityPlanApproved,
    BusinessContinuityPlanExercised,
)


class BusinessContinuityPlanTests(TestCase):
    """Tests for BusinessContinuityPlan aggregate"""
    
    def test_create_bcp(self):
        """Test creating a business continuity plan"""
        bcp = BusinessContinuityPlan()
        bcp.create(
            name="Data Center DR Plan",
            description="Disaster recovery plan for primary data center"
        )
        bcp.save()
        
        self.assertEqual(bcp.name, "Data Center DR Plan")
        self.assertEqual(bcp.lifecycle_state, BusinessContinuityPlan.LifecycleState.DRAFT)
        
        # Check event was raised
        events = bcp.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "BusinessContinuityPlanCreated")
    
    def test_approve_bcp(self):
        """Test approving a BCP"""
        bcp = BusinessContinuityPlan()
        bcp.create(name="Data Center DR Plan")
        bcp.save()
        
        bcp.approve()
        bcp.save()
        
        self.assertEqual(bcp.lifecycle_state, BusinessContinuityPlan.LifecycleState.APPROVED)
        
        # Check event was raised
        events = bcp.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "BusinessContinuityPlanApproved")
    
    def test_exercise_bcp(self):
        """Test exercising a BCP"""
        bcp = BusinessContinuityPlan()
        bcp.create(name="Data Center DR Plan")
        bcp.save()
        bcp.approve()
        bcp.save()
        
        bcp.exercise()
        bcp.save()
        
        self.assertEqual(bcp.lifecycle_state, BusinessContinuityPlan.LifecycleState.EXERCISED)
        
        # Check event was raised
        events = bcp.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "BusinessContinuityPlanExercised")
    
    def test_add_task(self):
        """Test adding a task to a BCP"""
        bcp = BusinessContinuityPlan()
        bcp.create(name="Data Center DR Plan")
        bcp.save()
        
        task_id = uuid.uuid4()
        bcp.add_task(task_id)
        bcp.save()
        
        self.assertIn(task_id, bcp.taskIds)

