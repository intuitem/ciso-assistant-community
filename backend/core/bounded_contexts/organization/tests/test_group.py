"""
Tests for Group aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.organization.aggregates.group import Group
from core.bounded_contexts.organization.domain_events import (
    GroupCreated,
    PermissionAddedToGroup,
    UserAddedToGroup,
)


class GroupTests(TestCase):
    """Tests for Group aggregate"""
    
    def test_create_group(self):
        """Test creating a group"""
        group = Group()
        group.create(
            name="Administrators",
            description="System administrators",
            builtin=False
        )
        group.save()
        
        self.assertEqual(group.name, "Administrators")
        self.assertEqual(group.lifecycle_state, Group.LifecycleState.ACTIVE)
        self.assertFalse(group.builtin)
        
        # Check event was raised
        events = group.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "GroupCreated")
    
    def test_add_permission(self):
        """Test adding a permission to a group"""
        group = Group()
        group.create(name="Test Group")
        group.save()
        
        permission_id = uuid.uuid4()
        group.add_permission(permission_id)
        group.save()
        
        self.assertIn(permission_id, group.permissionIds)
        
        # Check event was raised
        events = group.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "PermissionAddedToGroup")
    
    def test_add_user(self):
        """Test adding a user to a group"""
        group = Group()
        group.create(name="Test Group")
        group.save()
        
        user_id = uuid.uuid4()
        group.add_user(user_id)
        group.save()
        
        self.assertIn(user_id, group.userIds)
        
        # Check event was raised
        events = group.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "UserAddedToGroup")
    
    def test_cannot_retire_builtin_group(self):
        """Test that built-in groups cannot be retired"""
        group = Group()
        group.create(name="Built-in Group", builtin=True)
        group.save()
        
        with self.assertRaises(ValueError):
            group.retire()

