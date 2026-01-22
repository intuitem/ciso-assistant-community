"""
Tests for Requirement aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.compliance.aggregates.requirement import Requirement
from core.bounded_contexts.compliance.domain_events import (
    RequirementCreated,
    RequirementMappedToControl,
    RequirementRetired,
)


class RequirementTests(TestCase):
    """Tests for Requirement aggregate"""
    
    def test_create_requirement(self):
        """Test creating a requirement"""
        requirement = Requirement()
        framework_id = uuid.uuid4()
        
        requirement.create(
            framework_id=framework_id,
            code="AC-1",
            statement="Access control policy and procedures",
            description="Develop and document access control policies"
        )
        requirement.save()
        
        self.assertEqual(requirement.frameworkId, framework_id)
        self.assertEqual(requirement.code, "AC-1")
        self.assertEqual(requirement.lifecycle_state, Requirement.LifecycleState.ACTIVE)
        
        # Check event was raised
        events = requirement.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "RequirementCreated")
    
    def test_map_to_control(self):
        """Test mapping a requirement to a control"""
        requirement = Requirement()
        requirement.create(framework_id=uuid.uuid4(), code="AC-1", statement="Test")
        requirement.save()
        
        control_id = uuid.uuid4()
        requirement.map_to_control(control_id)
        requirement.save()
        
        self.assertIn(control_id, requirement.mappedControlIds)
        
        # Check event was raised
        events = requirement.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "RequirementMappedToControl")
    
    def test_retire_requirement(self):
        """Test retiring a requirement"""
        requirement = Requirement()
        requirement.create(framework_id=uuid.uuid4(), code="AC-1", statement="Test")
        requirement.save()
        
        requirement.retire()
        requirement.save()
        
        self.assertEqual(requirement.lifecycle_state, Requirement.LifecycleState.RETIRED)
        
        # Check event was raised
        events = requirement.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "RequirementRetired")

