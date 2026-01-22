"""
Tests for OrgUnit aggregate
"""

import uuid
from django.test import TestCase
from django.core.exceptions import ValidationError

from core.bounded_contexts.organization.aggregates.org_unit import OrgUnit
from core.bounded_contexts.organization.domain_events import (
    OrgUnitCreated,
    OrgUnitActivated,
    OrgUnitRetired,
)


class OrgUnitTests(TestCase):
    """Tests for OrgUnit aggregate"""
    
    def test_create_org_unit(self):
        """Test creating an organizational unit"""
        org_unit = OrgUnit()
        org_unit.create(
            name="IT Department",
            description="Information Technology",
            ref_id="IT-DEPT"
        )
        org_unit.save()
        
        self.assertEqual(org_unit.name, "IT Department")
        self.assertEqual(org_unit.lifecycle_state, OrgUnit.LifecycleState.DRAFT)
        self.assertEqual(org_unit.ref_id, "IT-DEPT")
        
        # Check event was raised
        events = org_unit.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "OrgUnitCreated")
    
    def test_activate_org_unit(self):
        """Test activating an organizational unit"""
        org_unit = OrgUnit()
        org_unit.create(name="IT Department")
        org_unit.save()
        
        org_unit.activate()
        org_unit.save()
        
        self.assertEqual(org_unit.lifecycle_state, OrgUnit.LifecycleState.ACTIVE)
        
        # Check event was raised
        events = org_unit.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "OrgUnitActivated")
    
    def test_retire_org_unit(self):
        """Test retiring an organizational unit"""
        org_unit = OrgUnit()
        org_unit.create(name="IT Department")
        org_unit.save()
        org_unit.activate()
        org_unit.save()
        
        org_unit.retire()
        org_unit.save()
        
        self.assertEqual(org_unit.lifecycle_state, OrgUnit.LifecycleState.RETIRED)
        
        # Check event was raised
        events = org_unit.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "OrgUnitRetired")
    
    def test_add_child_org_unit(self):
        """Test adding a child organizational unit"""
        parent = OrgUnit()
        parent.create(name="IT Department")
        parent.save()
        
        child_id = uuid.uuid4()
        parent.add_child(child_id)
        parent.save()
        
        self.assertIn(child_id, parent.childOrgUnitIds)
        
        # Check event was raised
        events = parent.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ChildOrgUnitAdded")
    
    def test_assign_owner(self):
        """Test assigning an owner to organizational unit"""
        org_unit = OrgUnit()
        org_unit.create(name="IT Department")
        org_unit.save()
        
        owner_id = uuid.uuid4()
        org_unit.assign_owner(owner_id)
        org_unit.save()
        
        self.assertIn(owner_id, org_unit.ownerUserIds)
        
        # Check event was raised
        events = org_unit.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "OwnerAssignedToOrgUnit")
    
    def test_cannot_retire_with_active_children(self):
        """Test that retiring fails if there are active children"""
        parent = OrgUnit()
        parent.create(name="Parent")
        parent.save()
        parent.activate()
        parent.save()
        
        child = OrgUnit()
        child.create(name="Child", parent_id=parent.id)
        child.save()
        child.activate()
        child.save()
        
        parent.add_child(child.id)
        parent.save()
        
        # Should raise ValidationError
        with self.assertRaises(ValidationError):
            parent.retire()

