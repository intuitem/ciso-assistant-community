"""
Tests for AwarenessProgram aggregate
"""

from django.test import TestCase

from core.bounded_contexts.security_operations.aggregates.awareness_program import AwarenessProgram
from core.bounded_contexts.security_operations.domain_events import (
    AwarenessProgramCreated,
    AwarenessProgramActivated,
)


class AwarenessProgramTests(TestCase):
    """Tests for AwarenessProgram aggregate"""
    
    def test_create_program(self):
        """Test creating an awareness program"""
        program = AwarenessProgram()
        program.create(
            name="Security Awareness 2024",
            description="Annual security awareness training",
            cadence_days=30
        )
        program.save()
        
        self.assertEqual(program.name, "Security Awareness 2024")
        self.assertEqual(program.cadence_days, 30)
        self.assertEqual(program.lifecycle_state, AwarenessProgram.LifecycleState.DRAFT)
        
        # Check event was raised
        events = program.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "AwarenessProgramCreated")
    
    def test_activate_program(self):
        """Test activating a program"""
        program = AwarenessProgram()
        program.create(name="Security Awareness 2024")
        program.save()
        
        program.activate()
        program.save()
        
        self.assertEqual(program.lifecycle_state, AwarenessProgram.LifecycleState.ACTIVE)
        
        # Check event was raised
        events = program.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "AwarenessProgramActivated")

