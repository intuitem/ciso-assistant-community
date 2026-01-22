"""
Tests for aggregate root infrastructure
"""

import uuid
from django.test import TestCase
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.events import DomainEvent, get_event_bus


class TestEvent(DomainEvent):
    """Test domain event"""
    pass


class TestAggregate(AggregateRoot):
    """Test aggregate root"""
    
    name = models.CharField(max_length=255)
    
    def create(self):
        """Create the aggregate and raise event"""
        self._raise_event(TestEvent(
            payload={"action": "created", "name": self.name}
        ))


class AggregateRootTests(TestCase):
    """Tests for AggregateRoot"""
    
    def test_aggregate_has_id(self):
        """Test that aggregate has UUID ID"""
        aggregate = TestAggregate(name="Test")
        aggregate.save()
        
        self.assertIsNotNone(aggregate.id)
        self.assertIsInstance(aggregate.id, uuid.UUID)
    
    def test_aggregate_versioning(self):
        """Test optimistic locking version"""
        aggregate = TestAggregate(name="Test")
        aggregate.save()
        
        initial_version = aggregate.version
        
        aggregate.name = "Updated"
        aggregate.save()
        
        self.assertEqual(aggregate.version, initial_version + 1)
    
    def test_raise_event(self):
        """Test raising domain events"""
        aggregate = TestAggregate(name="Test")
        aggregate.create()
        
        events = aggregate.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "TestEvent")
    
    def test_events_published_on_save(self):
        """Test that events are published when aggregate is saved"""
        handler_called = []
        
        class TestHandler:
            def handle(self, event):
                handler_called.append(event)
        
        handler = TestHandler()
        event_bus = get_event_bus()
        event_bus.subscribe("TestEvent", handler)
        
        aggregate = TestAggregate(name="Test")
        aggregate.create()
        aggregate.save()
        
        # Check event was published
        self.assertEqual(len(handler_called), 1)
        self.assertEqual(handler_called[0].event_type, "TestEvent")
        
        # Check events are cleared
        self.assertEqual(len(aggregate.get_uncommitted_events()), 0)

