# DDD Infrastructure Documentation

## Overview

This module provides the foundation for Domain-Driven Design (DDD) patterns in CISO Assistant. It includes:

- **Domain Events**: Event-driven architecture for integration and read models
- **Aggregate Roots**: Base classes for aggregates with event publishing
- **Value Objects**: Immutable value objects
- **Repositories**: Collection-like interface for aggregates
- **Custom Fields**: Embedded ID arrays for aggregate-centric modeling

## Quick Start

### 1. Create an Aggregate Root

```python
from core.domain.aggregate import AggregateRoot
from core.domain.events import DomainEvent
from core.domain.fields import EmbeddedIdArrayField
from django.db import models
import uuid

class AssetCreated(DomainEvent):
    """Domain event for asset creation"""
    pass

class Asset(AggregateRoot):
    """Asset aggregate root"""
    
    name = models.CharField(max_length=255)
    controlIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of control IDs"
    )
    
    def create(self, name: str):
        """Create an asset"""
        self.name = name
        self._raise_event(AssetCreated(
            payload={"name": name}
        ))
```

### 2. Use a Repository

```python
from core.domain.repository import Repository
from core.domain.aggregate import Asset

class AssetRepository(Repository[Asset]):
    """Repository for Asset aggregates"""
    
    def __init__(self):
        super().__init__(Asset)
    
    def find_by_name(self, name: str):
        """Find asset by name"""
        return Asset.objects.filter(name=name).first()

# Usage
repository = AssetRepository()
asset = repository.get_by_id(asset_id)
```

### 3. Handle Domain Events

```python
from core.domain.events import EventHandler, DomainEvent, get_event_bus

class AssetCreatedHandler(EventHandler):
    """Handler for AssetCreated events"""
    
    def handle(self, event: DomainEvent):
        # Update read model, send notification, etc.
        print(f"Asset created: {event.payload['name']}")

# Subscribe handler
event_bus = get_event_bus()
event_bus.subscribe("AssetCreated", AssetCreatedHandler())
```

### 4. Use Value Objects

```python
from core.domain.value_object import ValueObject
from dataclasses import dataclass

@dataclass(frozen=True)
class RiskScoring(ValueObject):
    """Risk scoring value object"""
    likelihood: int
    impact: int
    inherent_score: int
    residual_score: int

# Usage
scoring = RiskScoring(
    likelihood=3,
    impact=4,
    inherent_score=12,
    residual_score=8
)
```

## Migration Utilities

### Migrate ManyToMany to Embedded ID Array

```python
from core.domain.migration_utils import migrate_manytomany_to_id_array

# Migrate Asset.controls (ManyToMany) to Asset.controlIds (ID array)
migrated_count = migrate_manytomany_to_id_array(
    model_class=Asset,
    field_name="controls",
    related_model_class=Control,
    id_array_field_name="controlIds"
)

print(f"Migrated {migrated_count} records")
```

### Validate Migration

```python
from core.domain.migration_utils import validate_migration

results = validate_migration(
    model_class=Asset,
    old_field_name="controls",
    new_field_name="controlIds",
    related_model_class=Control
)

print(f"Valid: {results['valid_records']}")
print(f"Invalid: {results['invalid_records']}")
```

## Testing

Run DDD infrastructure tests:

```bash
# Run all DDD tests
pytest core/domain/tests/ -c pytest_ddd.ini

# Run with coverage
pytest core/domain/tests/ -c pytest_ddd.ini --cov=core.domain

# Run specific test file
pytest core/domain/tests/test_events.py -c pytest_ddd.ini
```

## Architecture

### Event Flow

```
Aggregate.save()
  ↓
Raise Domain Events
  ↓
EventBus.publish()
  ↓
Store in EventStore
  ↓
Notify Handlers
  ↓
Update Read Models
```

### Aggregate Structure

```
AggregateRoot
├── id: UUID
├── version: int (optimistic locking)
├── _domain_events: List[DomainEvent]
├── _raise_event(event)
└── _apply_event(event)
```

## Best Practices

1. **Aggregates should be small**: Keep aggregates focused and small
2. **Use embedded ID arrays**: For membership relationships within aggregates
3. **Use first-class associations**: When relationships have attributes or meaning
4. **Raise domain events**: For important domain occurrences
5. **Keep aggregates consistent**: Enforce invariants within aggregates
6. **Use repositories**: Abstract persistence details

## Examples

See `core/domain/tests/` for complete examples of:
- Creating aggregates
- Raising events
- Using repositories
- Handling events
- Using value objects
- Migrating from traditional patterns

## Next Steps

1. Review the test files for examples
2. Create your first aggregate
3. Define domain events
4. Set up event handlers
5. Migrate existing models gradually

