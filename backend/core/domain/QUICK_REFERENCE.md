# DDD Infrastructure Quick Reference

## Common Patterns

### Create Aggregate with Events

```python
from core.domain.aggregate import AggregateRoot
from core.domain.events import DomainEvent
from core.domain.fields import EmbeddedIdArrayField

class MyEvent(DomainEvent):
    pass

class MyAggregate(AggregateRoot):
    name = models.CharField(max_length=255)
    relatedIds = EmbeddedIdArrayField(models.UUIDField(), default=list)
    
    def do_something(self):
        self._raise_event(MyEvent(payload={"data": "value"}))
```

### Use Repository

```python
from core.domain.repository import Repository

repo = Repository(MyAggregate)
agg = repo.get_by_id(uuid)
all_aggs = repo.get_all()
repo.save(agg)
repo.delete(agg)
```

### Handle Events

```python
from core.domain.events import EventHandler, get_event_bus

class MyHandler(EventHandler):
    def handle(self, event):
        # Handle event
        pass

get_event_bus().subscribe("MyEvent", MyHandler())
```

### Use Value Objects

```python
from core.domain.value_object import ValueObject
from dataclasses import dataclass

@dataclass(frozen=True)
class MyValue(ValueObject):
    field1: int
    field2: str

value = MyValue(field1=1, field2="test")
data = value.to_dict()
reconstructed = MyValue.from_dict(data)
```

### Migrate ManyToMany to ID Array

```python
from core.domain.migration_utils import migrate_manytomany_to_id_array

count = migrate_manytomany_to_id_array(
    model_class=Asset,
    field_name="controls",
    related_model_class=Control,
    id_array_field_name="controlIds"
)
```

## Common Commands

```bash
# Run tests
make test-ddd

# Check coverage
make test-coverage

# Run migrations
python manage.py migrate core.domain

# Verify EventStore
python manage.py shell
>>> from core.domain.events import EventStore
>>> EventStore.objects.count()
```

## File Locations

- Infrastructure: `core/domain/*.py`
- Tests: `core/domain/tests/*.py`
- Examples: `core/domain/examples/*.py`
- Docs: `core/domain/README.md`

