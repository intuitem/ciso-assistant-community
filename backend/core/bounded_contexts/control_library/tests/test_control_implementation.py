"""
Tests for ControlImplementation association
"""

import uuid
from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone

from core.bounded_contexts.control_library.associations.control_implementation import ControlImplementation
from core.bounded_contexts.control_library.domain_events import (
    ControlImplementationCreated,
    ControlImplementationStatusChanged,
    ControlImplementationTested,
)


class ControlImplementationTests(TestCase):
    """Tests for ControlImplementation association"""
    
    def test_create_implementation(self):
        """Test creating a control implementation"""
        impl = ControlImplementation()
        control_id = uuid.uuid4()
        asset_id = uuid.uuid4()
        
        impl.create(
            control_id=control_id,
            target_type="asset",
            target_id=asset_id,
            frequency="monthly"
        )
        impl.save()
        
        self.assertEqual(impl.controlId, control_id)
        self.assertEqual(impl.target_type, "asset")
        self.assertEqual(impl.target_id, asset_id)
        self.assertEqual(impl.lifecycle_state, ControlImplementation.LifecycleState.PLANNED)
        self.assertEqual(impl.frequency, "monthly")
        
        # Check event was raised
        events = impl.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ControlImplementationCreated")
    
    def test_mark_implemented(self):
        """Test marking implementation as implemented"""
        impl = ControlImplementation()
        impl.create(
            control_id=uuid.uuid4(),
            target_type="asset",
            target_id=uuid.uuid4()
        )
        impl.save()
        
        impl.mark_implemented()
        impl.save()
        
        self.assertEqual(impl.lifecycle_state, ControlImplementation.LifecycleState.IMPLEMENTED)
        
        # Check event was raised
        events = impl.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ControlImplementationStatusChanged")
    
    def test_mark_operating(self):
        """Test marking implementation as operating"""
        impl = ControlImplementation()
        impl.create(
            control_id=uuid.uuid4(),
            target_type="asset",
            target_id=uuid.uuid4()
        )
        impl.save()
        impl.mark_implemented()
        impl.save()
        
        impl.mark_operating()
        impl.save()
        
        self.assertEqual(impl.lifecycle_state, ControlImplementation.LifecycleState.OPERATING)
    
    def test_record_test(self):
        """Test recording a test of the implementation"""
        impl = ControlImplementation()
        impl.create(
            control_id=uuid.uuid4(),
            target_type="asset",
            target_id=uuid.uuid4()
        )
        impl.save()
        impl.mark_implemented()
        impl.save()
        
        impl.record_test(effectiveness_rating=4)
        impl.save()
        
        self.assertEqual(impl.effectiveness_rating, 4)
        self.assertIsNotNone(impl.last_tested_at)
        # Should automatically mark as operating if rating >= 3
        self.assertEqual(impl.lifecycle_state, ControlImplementation.LifecycleState.OPERATING)
        
        # Check event was raised
        events = impl.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ControlImplementationTested")
    
    def test_record_test_invalid_rating(self):
        """Test that invalid effectiveness rating raises error"""
        impl = ControlImplementation()
        impl.create(
            control_id=uuid.uuid4(),
            target_type="asset",
            target_id=uuid.uuid4()
        )
        impl.save()
        
        with self.assertRaises(ValueError):
            impl.record_test(effectiveness_rating=6)
    
    def test_add_evidence(self):
        """Test adding evidence to an implementation"""
        impl = ControlImplementation()
        impl.create(
            control_id=uuid.uuid4(),
            target_type="asset",
            target_id=uuid.uuid4()
        )
        impl.save()
        
        evidence_id = uuid.uuid4()
        impl.add_evidence(evidence_id)
        impl.save()
        
        self.assertIn(evidence_id, impl.evidenceIds)

