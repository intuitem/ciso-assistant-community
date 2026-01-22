"""
Tests for ComplianceFramework aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.compliance.aggregates.compliance_framework import ComplianceFramework
from core.bounded_contexts.compliance.domain_events import (
    ComplianceFrameworkCreated,
    ComplianceFrameworkActivated,
    ComplianceFrameworkRetired,
)


class ComplianceFrameworkTests(TestCase):
    """Tests for ComplianceFramework aggregate"""
    
    def test_create_framework(self):
        """Test creating a compliance framework"""
        framework = ComplianceFramework()
        framework.create(
            name="NIST 800-53",
            version="Rev 5",
            description="NIST Cybersecurity Framework"
        )
        framework.save()
        
        self.assertEqual(framework.name, "NIST 800-53")
        self.assertEqual(framework.version, "Rev 5")
        self.assertEqual(framework.lifecycle_state, ComplianceFramework.LifecycleState.DRAFT)
        
        # Check event was raised
        events = framework.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ComplianceFrameworkCreated")
    
    def test_activate_framework(self):
        """Test activating a framework"""
        framework = ComplianceFramework()
        framework.create(name="NIST 800-53")
        framework.save()
        
        framework.activate()
        framework.save()
        
        self.assertEqual(framework.lifecycle_state, ComplianceFramework.LifecycleState.ACTIVE)
        
        # Check event was raised
        events = framework.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ComplianceFrameworkActivated")
    
    def test_retire_framework(self):
        """Test retiring a framework"""
        framework = ComplianceFramework()
        framework.create(name="NIST 800-53")
        framework.save()
        framework.activate()
        framework.save()
        
        framework.retire()
        framework.save()
        
        self.assertEqual(framework.lifecycle_state, ComplianceFramework.LifecycleState.RETIRED)
        
        # Check event was raised
        events = framework.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ComplianceFrameworkRetired")
    
    def test_add_requirement(self):
        """Test adding a requirement to a framework"""
        framework = ComplianceFramework()
        framework.create(name="NIST 800-53")
        framework.save()
        
        requirement_id = uuid.uuid4()
        framework.add_requirement(requirement_id)
        framework.save()
        
        self.assertIn(requirement_id, framework.requirementIds)

