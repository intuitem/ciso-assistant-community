"""
Tests for Process aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.asset_and_service.aggregates.process import Process
from core.bounded_contexts.asset_and_service.domain_events import (
    ProcessCreated,
    ProcessActivated,
    ProcessRetired,
)


class ProcessTests(TestCase):
    """Tests for Process aggregate"""
    
    def test_create_process(self):
        """Test creating a process"""
        process = Process()
        process.create(
            name="Customer Onboarding",
            description="Process for onboarding new customers",
            ref_id="CO-001"
        )
        process.save()
        
        self.assertEqual(process.name, "Customer Onboarding")
        self.assertEqual(process.lifecycle_state, Process.LifecycleState.DRAFT)
        self.assertEqual(process.ref_id, "CO-001")
        
        # Check event was raised
        events = process.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ProcessCreated")
    
    def test_activate_process(self):
        """Test activating a process"""
        process = Process()
        process.create(name="Customer Onboarding")
        process.save()
        
        process.activate()
        process.save()
        
        self.assertEqual(process.lifecycle_state, Process.LifecycleState.ACTIVE)
        
        # Check event was raised
        events = process.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ProcessActivated")
    
    def test_retire_process(self):
        """Test retiring a process"""
        process = Process()
        process.create(name="Customer Onboarding")
        process.save()
        process.activate()
        process.save()
        
        process.retire()
        process.save()
        
        self.assertEqual(process.lifecycle_state, Process.LifecycleState.RETIRED)
        
        # Check event was raised
        events = process.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ProcessRetired")

