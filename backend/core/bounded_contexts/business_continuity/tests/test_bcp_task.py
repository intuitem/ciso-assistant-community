"""
Tests for BcpTask supporting entity
"""

import uuid
from datetime import date
from django.test import TestCase

from core.bounded_contexts.business_continuity.supporting_entities.bcp_task import BcpTask
from core.bounded_contexts.business_continuity.domain_events import (
    BcpTaskCreated,
    BcpTaskStatusChanged,
)


class BcpTaskTests(TestCase):
    """Tests for BcpTask supporting entity"""
    
    def test_create_task(self):
        """Test creating a BCP task"""
        task = BcpTask()
        bcp_id = uuid.uuid4()
        
        task.create(
            bcp_id=bcp_id,
            title="Test backup restoration",
            description="Verify backup restoration procedures",
            owner_user_id=uuid.uuid4(),
            due_date=date(2024, 12, 31)
        )
        task.save()
        
        self.assertEqual(task.bcpId, bcp_id)
        self.assertEqual(task.title, "Test backup restoration")
        self.assertEqual(task.lifecycle_state, BcpTask.LifecycleState.OPEN)
        
        # Check event was raised
        events = task.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "BcpTaskCreated")
    
    def test_start_task(self):
        """Test starting a task"""
        task = BcpTask()
        task.create(bcp_id=uuid.uuid4(), title="Test task")
        task.save()
        
        task.start()
        task.save()
        
        self.assertEqual(task.lifecycle_state, BcpTask.LifecycleState.IN_PROGRESS)
        
        # Check event was raised
        events = task.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "BcpTaskStatusChanged")
    
    def test_complete_task(self):
        """Test completing a task"""
        task = BcpTask()
        task.create(bcp_id=uuid.uuid4(), title="Test task")
        task.save()
        task.start()
        task.save()
        
        task.complete()
        task.save()
        
        self.assertEqual(task.lifecycle_state, BcpTask.LifecycleState.DONE)

