# Control Library Bounded Context

## Overview

The Control Library bounded context manages controls, policies, evidence, and their implementations using Domain-Driven Design (DDD) patterns.

## Quick Start

### 1. Register the App

The app is already registered in `ciso_assistant/settings.py`:

```python
INSTALLED_APPS = [
    # ...
    "core.bounded_contexts.control_library",
    # ...
]
```

### 2. Run Migrations

```bash
cd backend
python manage.py makemigrations core.bounded_contexts.control_library
python manage.py migrate core.bounded_contexts.control_library
```

### 3. Run Tests

```bash
pytest core/bounded_contexts/control_library/tests/ -v
```

### 4. Access API

The API is available at:
- `/api/control-library/controls/` - Controls
- `/api/control-library/policies/` - Policies
- `/api/control-library/evidence-items/` - Evidence items
- `/api/control-library/control-implementations/` - Control implementations
- `/api/control-library/policy-acknowledgements/` - Policy acknowledgements

## Architecture

### Aggregates

1. **Control** - Controls in the library
   - Lifecycle: Draft → Approved → Deprecated
   - Embedded arrays: `legalRequirementIds[]`, `relatedControlIds[]`

2. **Policy** - Policies
   - Lifecycle: Draft → Published → Retired
   - Embedded arrays: `ownerUserIds[]`, `relatedControlIds[]`, `applicableOrgUnitIds[]`

3. **EvidenceItem** - Evidence items
   - Lifecycle: Collected → Verified → Expired
   - Source types: Upload, Link, SystemRecord

### Associations

1. **ControlImplementation** - First-class association
   - Target types: Asset, Service, Process, ThirdParty, OrgUnit, DataFlow, DataAsset
   - Lifecycle: Planned → Implemented → Operating → Ineffective → Retired
   - Fields: frequency, lastTestedAt, effectivenessRating

2. **PolicyAcknowledgement** - First-class association
   - Methods: Clickwrap, Training, DocSign
   - Tracks: policy version, acknowledgedAt, method

### Read Models

1. **ControlOverview** - Denormalized for dashboards
   - Implementation count and status summary
   - Evidence count
   - Related control and legal requirement counts

## Usage Examples

### Create a Control

```python
from core.bounded_contexts.control_library.aggregates.control import Control
from core.bounded_contexts.control_library.repositories.control_repository import ControlRepository

repo = ControlRepository()
control = Control()
control.create(
    name="Access Control",
    objective="Control access to systems",
    ref_id="AC-1",
    control_type="technical"
)
repo.save(control)
control.approve()
repo.save(control)
```

### Create a Control Implementation

```python
from core.bounded_contexts.control_library.associations.control_implementation import ControlImplementation

impl = ControlImplementation()
impl.create(
    control_id=control_id,
    target_type="asset",
    target_id=asset_id,
    frequency="monthly"
)
impl.save()
impl.mark_implemented()
impl.save()
impl.record_test(effectiveness_rating=4)
impl.save()
```

### Acknowledge a Policy

```python
from core.bounded_contexts.control_library.associations.policy_acknowledgement import PolicyAcknowledgement

ack = PolicyAcknowledgement()
ack.acknowledge(
    policy_id=policy_id,
    policy_version="1.0",
    user_id=user_id,
    method="clickwrap"
)
ack.save()
```

## Domain Events

All aggregates raise domain events on state changes:

- `ControlCreated`, `ControlApproved`, `ControlDeprecated`
- `PolicyCreated`, `PolicyPublished`, `PolicyRetired`
- `EvidenceCollected`, `EvidenceVerified`, `EvidenceExpired`
- `ControlImplementationCreated`, `ControlImplementationStatusChanged`, `ControlImplementationTested`
- `PolicyAcknowledged`

Events are automatically stored in `EventStore` and can trigger projection handlers to update read models.

## Testing

Run all tests:

```bash
pytest core/bounded_contexts/control_library/tests/ -v
```

Run specific test file:

```bash
pytest core/bounded_contexts/control_library/tests/test_control.py -v
```

## API Documentation

### Control Endpoints

- `GET /api/control-library/controls/` - List all controls
- `POST /api/control-library/controls/` - Create control
- `GET /api/control-library/controls/{id}/` - Get control
- `PUT /api/control-library/controls/{id}/` - Update control
- `DELETE /api/control-library/controls/{id}/` - Delete control
- `POST /api/control-library/controls/{id}/approve/` - Approve control
- `POST /api/control-library/controls/{id}/deprecate/` - Deprecate control

### Policy Endpoints

- `GET /api/control-library/policies/` - List all policies
- `POST /api/control-library/policies/` - Create policy
- `GET /api/control-library/policies/{id}/` - Get policy
- `PUT /api/control-library/policies/{id}/` - Update policy
- `DELETE /api/control-library/policies/{id}/` - Delete policy
- `POST /api/control-library/policies/{id}/publish/` - Publish policy
- `POST /api/control-library/policies/{id}/retire/` - Retire policy

### EvidenceItem Endpoints

- `GET /api/control-library/evidence-items/` - List all evidence items
- `POST /api/control-library/evidence-items/` - Create evidence item
- `GET /api/control-library/evidence-items/{id}/` - Get evidence item
- `PUT /api/control-library/evidence-items/{id}/` - Update evidence item
- `DELETE /api/control-library/evidence-items/{id}/` - Delete evidence item
- `POST /api/control-library/evidence-items/{id}/verify/` - Verify evidence
- `POST /api/control-library/evidence-items/{id}/expire/` - Expire evidence

### ControlImplementation Endpoints

- `GET /api/control-library/control-implementations/` - List all implementations
- `POST /api/control-library/control-implementations/` - Create implementation
- `GET /api/control-library/control-implementations/{id}/` - Get implementation
- `PUT /api/control-library/control-implementations/{id}/` - Update implementation
- `DELETE /api/control-library/control-implementations/{id}/` - Delete implementation
- `POST /api/control-library/control-implementations/{id}/mark_implemented/` - Mark as implemented
- `POST /api/control-library/control-implementations/{id}/mark_operating/` - Mark as operating
- `POST /api/control-library/control-implementations/{id}/record_test/` - Record test

### PolicyAcknowledgement Endpoints

- `GET /api/control-library/policy-acknowledgements/` - List all acknowledgements
- `POST /api/control-library/policy-acknowledgements/` - Create acknowledgement
- `GET /api/control-library/policy-acknowledgements/{id}/` - Get acknowledgement
- `PUT /api/control-library/policy-acknowledgements/{id}/` - Update acknowledgement
- `DELETE /api/control-library/policy-acknowledgements/{id}/` - Delete acknowledgement

## Filtering and Search

All endpoints support filtering, searching, and ordering:

- Filtering: `?lifecycle_state=approved&control_type=technical`
- Search: `?search=access`
- Ordering: `?ordering=name` or `?ordering=-created_at`

## Next Steps

1. **Data Migration**: Migrate existing `core.ReferenceControl` → `control_library.Control`
2. **Frontend Integration**: Update UI to use new endpoints
3. **Performance Testing**: Test with large datasets
4. **Documentation**: Add OpenAPI/Swagger documentation

## Related Documentation

- [DDD Infrastructure](../../domain/README.md)
- [Phase 3 Completion Guide](../../../../PHASE_3_CONTROL_LIBRARY_COMPLETE.md)
- [Refined Comprehensive Plan](../../../../REFINED_COMPREHENSIVE_PLAN.md)

