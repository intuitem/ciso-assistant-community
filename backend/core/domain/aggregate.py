"""
Aggregate Root and Entity Base Classes

Aggregates are clusters of domain objects that can be treated
as a single unit for data changes.
"""

import uuid
from typing import List, Optional
from django.db import models
from django.utils import timezone
from .events import DomainEvent, get_event_bus


class AggregateRoot(models.Model):
    """
    Base class for aggregate roots.

    Aggregate roots:
    - Have a unique identity (UUID)
    - Maintain consistency boundaries
    - Raise domain events
    - Use optimistic locking (version)
    - Track audit information (user context)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.IntegerField(default=0, help_text="Optimistic locking version")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Audit fields for compliance and user tracking
    created_by = models.UUIDField(null=True, blank=True, help_text="User who created this record")
    updated_by = models.UUIDField(null=True, blank=True, help_text="User who last updated this record")
    
    # Uncommitted domain events (not persisted)
    _domain_events: List[DomainEvent] = []
    
    class Meta:
        abstract = True
    
    def _raise_event(self, event: DomainEvent):
        """
        Raise a domain event.
        
        Events are collected and published when the aggregate is saved.
        """
        event.aggregate_id = self.id
        event.aggregate_version = self.version
        self._domain_events.append(event)
    
    def _apply_event(self, event: DomainEvent):
        """
        Apply a domain event to the aggregate.
        
        This is used for event sourcing or read model updates.
        Subclasses can override to handle specific events.
        """
        pass
    
    def get_uncommitted_events(self) -> List[DomainEvent]:
        """Get uncommitted domain events"""
        return list(self._domain_events)
    
    def mark_events_as_committed(self):
        """Clear uncommitted events after they've been published"""
        self._domain_events.clear()
    
    def save(self, *args, **kwargs):
        """Override save to publish domain events"""
        # Increment version for optimistic locking
        if self.pk:
            self.version += 1
        
        # Save the aggregate
        super().save(*args, **kwargs)
        
        # Publish domain events
        event_bus = get_event_bus()
        for event in self._domain_events:
            event_bus.publish(event, store=True)
        
        # Clear uncommitted events
        self.mark_events_as_committed()
    
    def __str__(self):
        return f"{self.__class__.__name__}({self.id})"


class Entity(models.Model):
    """
    Base class for entities within an aggregate.
    
    Entities have identity but are not aggregate roots.
    They belong to an aggregate root.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
    
    def __str__(self):
        return f"{self.__class__.__name__}({self.id})"

