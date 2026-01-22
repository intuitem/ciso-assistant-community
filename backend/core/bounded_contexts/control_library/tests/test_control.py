"""
Tests for Control aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.control_library.aggregates.control import Control
from core.bounded_contexts.control_library.domain_events import (
    ControlCreated,
    ControlApproved,
    ControlDeprecated,
)


class ControlTests(TestCase):
    """Tests for Control aggregate"""
    
    def test_create_control(self):
        """Test creating a control"""
        control = Control()
        control.create(
            name="Access Control",
            objective="Control access to systems",
            ref_id="AC-1",
            control_type="technical"
        )
        control.save()
        
        self.assertEqual(control.name, "Access Control")
        self.assertEqual(control.lifecycle_state, Control.LifecycleState.DRAFT)
        self.assertEqual(control.ref_id, "AC-1")
        self.assertEqual(control.control_type, "technical")
        
        # Check event was raised
        events = control.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ControlCreated")
    
    def test_approve_control(self):
        """Test approving a control"""
        control = Control()
        control.create(name="Access Control", ref_id="AC-1")
        control.save()
        
        control.approve()
        control.save()
        
        self.assertEqual(control.lifecycle_state, Control.LifecycleState.APPROVED)
        
        # Check event was raised
        events = control.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ControlApproved")
    
    def test_deprecate_control(self):
        """Test deprecating a control"""
        control = Control()
        control.create(name="Access Control", ref_id="AC-1")
        control.save()
        control.approve()
        control.save()
        
        control.deprecate()
        control.save()
        
        self.assertEqual(control.lifecycle_state, Control.LifecycleState.DEPRECATED)
        
        # Check event was raised
        events = control.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ControlDeprecated")
    
    def test_add_legal_requirement(self):
        """Test adding a legal requirement to a control"""
        control = Control()
        control.create(name="Access Control")
        control.save()
        
        requirement_id = uuid.uuid4()
        control.add_legal_requirement(requirement_id)
        control.save()
        
        self.assertIn(requirement_id, control.legalRequirementIds)
    
    def test_add_related_control(self):
        """Test adding a related control"""
        control = Control()
        control.create(name="Access Control")
        control.save()
        
        related_id = uuid.uuid4()
        control.add_related_control(related_id)
        control.save()
        
        self.assertIn(related_id, control.relatedControlIds)

