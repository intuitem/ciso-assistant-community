"""
Tests for domain events infrastructure
"""

import uuid
from datetime import datetime
from django.test import TestCase
from django.utils import timezone

from core.domain.events import (
    DomainEvent,
    EventStore,
    EventBus,
    EventHandler,
    get_event_bus,
)


class TestDomainEvent(DomainEvent):
    """Test domain event"""
    pass


class TestEventHandler(EventHandler):
    """Test event handler"""
    
    def __init__(self):
        self.handled_events = []
    
    def handle(self, event: DomainEvent):
        self.handled_events.append(event)


class DomainEventTests(TestCase):
    """Tests for DomainEvent"""
    
    def test_event_creation(self):
        """Test creating a domain event"""
        event = TestDomainEvent(
            aggregate_id=uuid.uuid4(),
            aggregate_version=1,
            payload={"test": "data"}
        )
        
        self.assertIsNotNone(event.event_id)
        self.assertEqual(event.event_type, "TestDomainEvent")
        self.assertEqual(event.payload, {"test": "data"})
    
    def test_event_to_dict(self):
        """Test converting event to dictionary"""
        aggregate_id = uuid.uuid4()
        event = TestDomainEvent(
            aggregate_id=aggregate_id,
            aggregate_version=1,
            payload={"test": "data"}
        )
        
        data = event.to_dict()
        
        self.assertEqual(data["event_type"], "TestDomainEvent")
        self.assertEqual(data["aggregate_id"], str(aggregate_id))
        self.assertEqual(data["aggregate_version"], 1)
        self.assertEqual(data["payload"], {"test": "data"})
    
    def test_event_from_dict(self):
        """Test reconstructing event from dictionary"""
        aggregate_id = uuid.uuid4()
        event_id = uuid.uuid4()
        occurred_at = timezone.now()
        
        data = {
            "event_id": str(event_id),
            "aggregate_id": str(aggregate_id),
            "aggregate_version": 1,
            "occurred_at": occurred_at.isoformat(),
            "event_type": "TestDomainEvent",
            "payload": {"test": "data"}
        }
        
        event = DomainEvent.from_dict(data)
        
        self.assertEqual(event.event_id, event_id)
        self.assertEqual(event.aggregate_id, aggregate_id)
        self.assertEqual(event.aggregate_version, 1)
        self.assertEqual(event.payload, {"test": "data"})


class EventBusTests(TestCase):
    """Tests for EventBus"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.handler = TestEventHandler()
    
    def test_subscribe_handler(self):
        """Test subscribing a handler"""
        self.event_bus.subscribe("TestDomainEvent", self.handler)
        
        self.assertIn("TestDomainEvent", self.event_bus._handlers)
        self.assertIn(self.handler, self.event_bus._handlers["TestDomainEvent"])
    
    def test_publish_event(self):
        """Test publishing an event"""
        self.event_bus.subscribe("TestDomainEvent", self.handler)
        
        event = TestDomainEvent(
            aggregate_id=uuid.uuid4(),
            aggregate_version=1
        )
        
        self.event_bus.publish(event, store=False)
        
        self.assertEqual(len(self.handler.handled_events), 1)
        self.assertEqual(self.handler.handled_events[0], event)
    
    def test_publish_stores_event(self):
        """Test that publishing stores event in database"""
        event = TestDomainEvent(
            aggregate_id=uuid.uuid4(),
            aggregate_version=1,
            payload={"test": "data"}
        )
        
        self.event_bus.publish(event, store=True)
        
        # Check event was stored
        stored_event = EventStore.objects.get(event_id=event.event_id)
        self.assertEqual(stored_event.event_type, "TestDomainEvent")
        self.assertEqual(stored_event.payload, {"test": "data"})
    
    def test_replay_events(self):
        """Test replaying events"""
        aggregate_id = uuid.uuid4()
        
        # Create and store events
        event1 = TestDomainEvent(aggregate_id=aggregate_id, aggregate_version=1)
        event2 = TestDomainEvent(aggregate_id=aggregate_id, aggregate_version=2)
        
        self.event_bus.publish(event1, store=True)
        self.event_bus.publish(event2, store=True)
        
        # Subscribe handler
        handler = TestEventHandler()
        self.event_bus.subscribe("TestDomainEvent", handler)
        
        # Replay events
        self.event_bus.replay_events(aggregate_id=aggregate_id)
        
        # Check handler received events
        self.assertEqual(len(handler.handled_events), 2)


class EventStoreTests(TestCase):
    """Tests for EventStore model"""
    
    def test_create_event_store(self):
        """Test creating an event store record"""
        event_id = uuid.uuid4()
        aggregate_id = uuid.uuid4()
        
        EventStore.objects.create(
            event_id=event_id,
            aggregate_id=aggregate_id,
            aggregate_version=1,
            occurred_at=timezone.now(),
            event_type="TestDomainEvent",
            payload={"test": "data"}
        )
        
        stored = EventStore.objects.get(event_id=event_id)
        self.assertEqual(stored.aggregate_id, aggregate_id)
        self.assertEqual(stored.event_type, "TestDomainEvent")

