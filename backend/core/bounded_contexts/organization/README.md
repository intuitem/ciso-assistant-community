# Organization Bounded Context

## Overview

The Organization bounded context manages organizational structure, users, groups, and responsibility assignments using Domain-Driven Design (DDD) patterns.

## Quick Start

### 1. Register the App

The app is already registered in `ciso_assistant/settings.py`:

```python
INSTALLED_APPS = [
    # ...
    "core.domain",
    "core.bounded_contexts.organization",
    # ...
]
```

### 2. Run Migrations

```bash
cd backend
python manage.py makemigrations core.bounded_contexts.organization
python manage.py migrate core.bounded_contexts.organization
```

### 3. Run Tests

```bash
pytest core/bounded_contexts/organization/tests/ -v
```

### 4. Access API

The API is available at:
- `/api/organization/org-units/` - Organizational units
- `/api/organization/users/` - Users
- `/api/organization/groups/` - Groups
- `/api/organization/responsibility-assignments/` - Responsibility assignments

## Architecture

### Aggregates

1. **OrgUnit** - Organizational units with hierarchy
   - Lifecycle: Draft → Active → Retired
   - Embedded arrays: `childOrgUnitIds[]`, `ownerUserIds[]`

2. **User** - Users in the organization
   - Lifecycle: Invited → Active → Disabled
   - Embedded arrays: `groupIds[]`, `orgUnitIds[]`

3. **Group** - User groups with permissions
   - Lifecycle: Active → Retired
   - Embedded arrays: `permissionIds[]`, `userIds[]`

### Associations

1. **ResponsibilityAssignment** - First-class association
   - Subject types: Asset, Process, Service, Risk, Control, Policy, Project, DataAsset, DataFlow, ThirdParty, OrgUnit
   - Fields: role, startDate, endDate, notes

### Read Models

1. **OrgUnitOverview** - Denormalized for dashboards
2. **UserOverview** - Denormalized for user dashboards

## Usage Examples

### Create an Organizational Unit

```python
from core.bounded_contexts.organization.aggregates.org_unit import OrgUnit
from core.bounded_contexts.organization.repositories.org_unit_repository import OrgUnitRepository

repo = OrgUnitRepository()
org_unit = OrgUnit()
org_unit.create(
    name="IT Department",
    description="Information Technology",
    ref_id="IT-DEPT"
)
repo.save(org_unit)
org_unit.activate()
repo.save(org_unit)
```

### Create a User

```python
from core.bounded_contexts.organization.aggregates.user import User
from core.bounded_contexts.organization.repositories.user_repository import UserRepository

repo = UserRepository()
user = User()
user.create(
    email="john.doe@example.com",
    display_name="John Doe",
    password="secure_password"
)
repo.save(user)
user.activate()
repo.save(user)
```

### Assign Responsibility

```python
from core.bounded_contexts.organization.associations.responsibility_assignment import ResponsibilityAssignment
from datetime import date

assignment = ResponsibilityAssignment()
assignment.assign(
    subject_type="asset",
    subject_id=asset_id,
    user_id=user_id,
    role="owner",
    start_date=date.today()
)
assignment.save()
```

## Domain Events

All aggregates raise domain events on state changes:

- `OrgUnitCreated`, `OrgUnitActivated`, `OrgUnitRetired`
- `UserCreated`, `UserActivated`, `UserDisabled`
- `GroupCreated`, `PermissionAddedToGroup`, `UserAddedToGroup`
- `ResponsibilityAssigned`, `ResponsibilityRevoked`

Events are automatically stored in `EventStore` and can trigger projection handlers to update read models.

## Testing

Run all tests:

```bash
pytest core/bounded_contexts/organization/tests/ -v
```

Run specific test file:

```bash
pytest core/bounded_contexts/organization/tests/test_org_unit.py -v
```

## API Documentation

### OrgUnit Endpoints

- `GET /api/organization/org-units/` - List all org units
- `POST /api/organization/org-units/` - Create org unit
- `GET /api/organization/org-units/{id}/` - Get org unit
- `PUT /api/organization/org-units/{id}/` - Update org unit
- `DELETE /api/organization/org-units/{id}/` - Delete org unit
- `POST /api/organization/org-units/{id}/activate/` - Activate org unit
- `POST /api/organization/org-units/{id}/retire/` - Retire org unit
- `POST /api/organization/org-units/{id}/add_child/` - Add child org unit
- `POST /api/organization/org-units/{id}/assign_owner/` - Assign owner

### User Endpoints

- `GET /api/organization/users/` - List all users
- `POST /api/organization/users/` - Create user
- `GET /api/organization/users/{id}/` - Get user
- `PUT /api/organization/users/{id}/` - Update user
- `DELETE /api/organization/users/{id}/` - Delete user
- `POST /api/organization/users/{id}/activate/` - Activate user
- `POST /api/organization/users/{id}/disable/` - Disable user
- `POST /api/organization/users/{id}/assign_to_group/` - Assign to group
- `POST /api/organization/users/{id}/assign_to_org_unit/` - Assign to org unit

### Group Endpoints

- `GET /api/organization/groups/` - List all groups
- `POST /api/organization/groups/` - Create group
- `GET /api/organization/groups/{id}/` - Get group
- `PUT /api/organization/groups/{id}/` - Update group
- `DELETE /api/organization/groups/{id}/` - Delete group
- `POST /api/organization/groups/{id}/add_permission/` - Add permission
- `POST /api/organization/groups/{id}/add_user/` - Add user

### ResponsibilityAssignment Endpoints

- `GET /api/organization/responsibility-assignments/` - List all assignments
- `POST /api/organization/responsibility-assignments/` - Create assignment
- `GET /api/organization/responsibility-assignments/{id}/` - Get assignment
- `PUT /api/organization/responsibility-assignments/{id}/` - Update assignment
- `DELETE /api/organization/responsibility-assignments/{id}/` - Delete assignment
- `POST /api/organization/responsibility-assignments/{id}/revoke/` - Revoke assignment

## Filtering and Search

All endpoints support filtering, searching, and ordering:

- Filtering: `?lifecycle_state=active&parentOrgUnitId={id}`
- Search: `?search=IT`
- Ordering: `?ordering=name` or `?ordering=-created_at`

## Next Steps

1. **Data Migration**: Migrate existing `iam.User` → `organization.User`
2. **Frontend Integration**: Update UI to use new endpoints
3. **Performance Testing**: Test with large datasets
4. **Documentation**: Add OpenAPI/Swagger documentation

## Related Documentation

- [DDD Infrastructure](../../domain/README.md)
- [Phase 1 Completion Guide](../../../../PHASE_1_COMPLETE.md)
- [Refined Comprehensive Plan](../../../../REFINED_COMPREHENSIVE_PLAN.md)

