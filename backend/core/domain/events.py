"""
Domain Events Infrastructure

Domain events represent something important that happened in the domain.
They are used for:
- Integration between bounded contexts
- Read model updates
- Audit logging
- Workflow triggers
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
from django.db import models
from django.utils import timezone


@dataclass
class DomainEvent:
    """
    Base class for all domain events.
    
    Domain events are immutable value objects that represent
    something important that happened in the domain.
    """
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    aggregate_id: uuid.UUID = None
    aggregate_version: int = 0
    occurred_at: datetime = field(default_factory=lambda: timezone.now())
    event_type: str = None
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set event_type from class name if not provided"""
        if self.event_type is None:
            self.event_type = self.__class__.__name__
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for storage"""
        return {
            "event_id": str(self.event_id),
            "aggregate_id": str(self.aggregate_id) if self.aggregate_id else None,
            "aggregate_version": self.aggregate_version,
            "occurred_at": self.occurred_at.isoformat(),
            "event_type": self.event_type,
            "payload": self.payload,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainEvent":
        """Reconstruct event from dictionary"""
        return cls(
            event_id=uuid.UUID(data["event_id"]),
            aggregate_id=uuid.UUID(data["aggregate_id"]) if data.get("aggregate_id") else None,
            aggregate_version=data["aggregate_version"],
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
            event_type=data["event_type"],
            payload=data.get("payload", {}),
        )


class EventStore(models.Model):
    """
    Event store for domain events.
    
    Uses PostgreSQL JSONB for efficient storage and querying.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    event_id = models.UUIDField(unique=True, db_index=True)
    aggregate_id = models.UUIDField(db_index=True, null=True, blank=True)
    aggregate_version = models.IntegerField(default=0)
    occurred_at = models.DateTimeField(db_index=True)
    event_type = models.CharField(max_length=255, db_index=True)
    payload = models.JSONField()
    
    class Meta:
        db_table = "domain_events"
        ordering = ["occurred_at"]
        indexes = [
            models.Index(fields=["aggregate_id", "aggregate_version"]),
            models.Index(fields=["event_type", "occurred_at"]),
        ]
    
    def __str__(self):
        return f"{self.event_type} ({self.event_id})"


class EventBus:
    """
    Event bus for publishing and subscribing to domain events.
    
    Supports:
    - Synchronous event publishing
    - Event handler registration
    - Event replay for read models
    """
    
    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._store_events = True
    
    def subscribe(self, event_type: str, handler: "EventHandler"):
        """Subscribe a handler to an event type"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: str, handler: "EventHandler"):
        """Unsubscribe a handler from an event type"""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
    
    def publish(self, event: DomainEvent, store: bool = True):
        """
        Publish a domain event.
        
        Args:
            event: The domain event to publish
            store: Whether to store the event in the event store
        """
        # Store event if enabled
        if store and self._store_events:
            EventStore.objects.create(
                event_id=event.event_id,
                aggregate_id=event.aggregate_id,
                aggregate_version=event.aggregate_version,
                occurred_at=event.occurred_at,
                event_type=event.event_type,
                payload=event.payload,
            )
        
        # Notify handlers
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler.handle(event)
            except Exception as e:
                # Log error but don't fail event publishing
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error handling event {event.event_type}: {e}", exc_info=True)
    
    def replay_events(self, aggregate_id: Optional[uuid.UUID] = None, 
                      event_type: Optional[str] = None,
                      since: Optional[datetime] = None):
        """
        Replay events for read model updates.
        
        Args:
            aggregate_id: Filter by aggregate ID
            event_type: Filter by event type
            since: Filter events since this datetime
        """
        queryset = EventStore.objects.all()
        
        if aggregate_id:
            queryset = queryset.filter(aggregate_id=aggregate_id)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if since:
            queryset = queryset.filter(occurred_at__gte=since)
        
        for event_record in queryset.order_by("occurred_at"):
            event = DomainEvent.from_dict({
                "event_id": str(event_record.event_id),
                "aggregate_id": str(event_record.aggregate_id) if event_record.aggregate_id else None,
                "aggregate_version": event_record.aggregate_version,
                "occurred_at": event_record.occurred_at.isoformat(),
                "event_type": event_record.event_type,
                "payload": event_record.payload,
            })
            
            # Notify handlers
            handlers = self._handlers.get(event.event_type, [])
            for handler in handlers:
                handler.handle(event)


class EventHandler:
    """
    Base class for event handlers.
    
    Subclasses should implement the handle method.
    """
    
    def handle(self, event: DomainEvent):
        """
        Handle a domain event.
        
        Args:
            event: The domain event to handle
        """
        raise NotImplementedError("Subclasses must implement handle method")


# Global event bus instance
_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    return _event_bus

