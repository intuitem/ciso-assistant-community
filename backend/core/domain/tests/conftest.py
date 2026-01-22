"""
Pytest configuration for DDD domain tests
"""

import pytest
from django.test import TransactionTestCase
from django.db import transaction

from core.domain.events import EventBus, get_event_bus


@pytest.fixture
def event_bus():
    """Provide a clean event bus for each test"""
    bus = EventBus()
    bus._store_events = False  # Don't store events in tests unless needed
    return bus


@pytest.fixture
def stored_event_bus():
    """Provide an event bus that stores events"""
    bus = EventBus()
    bus._store_events = True
    return bus


@pytest.fixture(autouse=True)
def reset_event_bus():
    """Reset event bus handlers before each test"""
    bus = get_event_bus()
    bus._handlers.clear()
    yield
    bus._handlers.clear()


@pytest.fixture
def db_transaction():
    """Provide database transaction for tests"""
    with transaction.atomic():
        yield
        transaction.rollback()

