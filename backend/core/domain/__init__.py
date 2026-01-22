"""
Domain-Driven Design (DDD) Infrastructure

This module provides the foundation for DDD patterns including:
- Domain events
- Aggregate roots
- Value objects
- Bounded contexts
- Read models
"""

from .events import DomainEvent, EventBus, EventHandler
from .aggregate import AggregateRoot, Entity
from .value_object import ValueObject
from .repository import Repository

__all__ = [
    "DomainEvent",
    "EventBus",
    "EventHandler",
    "AggregateRoot",
    "Entity",
    "ValueObject",
    "Repository",
]

