# Risk Registers Bounded Context

## Overview

The Risk Registers bounded context manages three types of risks (Asset, Third Party, and Business) using Domain-Driven Design (DDD) patterns. It includes risk scoring, treatment plans, and exception management.

## Quick Start

### 1. Register the App

The app is already registered in `ciso_assistant/settings.py`:

```python
INSTALLED_APPS = [
    # ...
    "core.bounded_contexts.risk_registers",
    # ...
]
```

### 2. Run Migrations

```bash
cd backend
python manage.py makemigrations core.bounded_contexts.risk_registers
python manage.py migrate core.bounded_contexts.risk_registers
```

### 3. Run Tests

```bash
pytest core/bounded_contexts/risk_registers/tests/ -v
```

### 4. Access API

The API is available at:
- `/api/risk-registers/asset-risks/` - Asset risks
- `/api/risk-registers/third-party-risks/` - Third party risks
- `/api/risk-registers/business-risks/` - Business risks
- `/api/risk-registers/risk-treatment-plans/` - Treatment plans
- `/api/risk-registers/risk-exceptions/` - Risk exceptions

## Architecture

### Aggregates

1. **AssetRisk** - Risks associated with assets
   - Lifecycle: Draft → Assessed → Treated → Accepted → Closed
   - Fields: title, description, threat, vulnerability
   - Embedded arrays: `assetIds[]`, `controlImplementationIds[]`, `exceptionIds[]`, `relatedRiskIds[]`
   - Risk scoring stored as JSON

2. **ThirdPartyRisk** - Risks associated with third parties
   - Lifecycle: Draft → Assessed → Treated → Accepted → Closed
   - Embedded arrays: `thirdPartyIds[]`, `serviceIds[]`, `controlImplementationIds[]`, `assessmentRunIds[]`, `exceptionIds[]`

3. **BusinessRisk** - Risks associated with business processes
   - Lifecycle: Draft → Assessed → Treated → Accepted → Closed
   - Embedded arrays: `processIds[]`, `orgUnitIds[]`, `controlImplementationIds[]`, `exceptionIds[]`

### Supporting Entities

1. **RiskException** - Exception approval workflow
   - Lifecycle: Requested → Approved → Expired → Revoked
   - Fields: riskId, reason, approvedByUserId, approvedAt, expiresAt

2. **RiskTreatmentPlan** - Treatment plans with tasks
   - Lifecycle: Draft → Active → Completed → Abandoned
   - Strategy: Avoid, Mitigate, Transfer, Accept
   - Tasks stored as JSON array

### Value Objects

1. **RiskScoring** - Immutable risk scoring
   - Fields: likelihood (1-5), impact (1-5), inherent_score, residual_score, rationale

### Read Models

1. **RiskRegisterOverview** - Denormalized for dashboards
   - Risk counts by state (draft, assessed, treated, accepted, closed)
   - Average inherent and residual scores
   - Grouped by risk type (asset, third_party, business)

## Usage Examples

### Create an Asset Risk

```python
from core.bounded_contexts.risk_registers.aggregates.asset_risk import AssetRisk
from core.bounded_contexts.risk_registers.repositories.asset_risk_repository import AssetRiskRepository

repo = AssetRiskRepository()
risk = AssetRisk()
risk.create(
    title="Data Breach Risk",
    description="Risk of unauthorized access to sensitive data",
    threat="Malicious actors",
    vulnerability="Weak access controls"
)
repo.save(risk)

# Assess the risk
risk.assess(
    likelihood=4,
    impact=5,
    inherent_score=20,
    residual_score=10,
    rationale="High likelihood, critical impact"
)
repo.save(risk)
```

### Create a Treatment Plan

```python
from core.bounded_contexts.risk_registers.supporting_entities.risk_treatment_plan import RiskTreatmentPlan

plan = RiskTreatmentPlan()
plan.create(
    risk_id=risk_id,
    name="Data Encryption Plan",
    strategy="mitigate",
    description="Implement encryption for sensitive data"
)
plan.save()

# Add tasks
plan.add_task(
    title="Implement encryption",
    owner_user_id=user_id,
    due_date=date.today() + timedelta(days=30),
    status="Open"
)
plan.save()

# Activate the plan
plan.activate()
plan.save()
```

### Request a Risk Exception

```python
from core.bounded_contexts.risk_registers.supporting_entities.risk_exception import RiskException

exception = RiskException()
exception.create(
    risk_id=risk_id,
    reason="Temporary exception for testing",
    description="This is a test exception",
    expires_at=timezone.now() + timedelta(days=30)
)
exception.save()

# Approve the exception
exception.approve(approved_by_user_id=approver_id)
exception.save()
```

## Domain Events

All aggregates raise domain events on state changes:

- `AssetRiskCreated`, `AssetRiskAssessed`, `AssetRiskTreated`, `AssetRiskAccepted`, `AssetRiskClosed`
- `ThirdPartyRiskCreated`, `ThirdPartyRiskAssessed`, `ThirdPartyRiskTreated`, `ThirdPartyRiskAccepted`, `ThirdPartyRiskClosed`
- `BusinessRiskCreated`, `BusinessRiskAssessed`, `BusinessRiskTreated`, `BusinessRiskAccepted`, `BusinessRiskClosed`
- `RiskExceptionRequested`, `RiskExceptionApproved`, `RiskExceptionExpired`, `RiskExceptionRevoked`
- `RiskTreatmentPlanCreated`, `RiskTreatmentPlanActivated`, `RiskTreatmentPlanCompleted`, `RiskTreatmentPlanAbandoned`

Events are automatically stored in `EventStore` and can trigger projection handlers to update read models.

## Testing

Run all tests:

```bash
pytest core/bounded_contexts/risk_registers/tests/ -v
```

Run specific test file:

```bash
pytest core/bounded_contexts/risk_registers/tests/test_asset_risk.py -v
```

## API Documentation

### AssetRisk Endpoints

- `GET /api/risk-registers/asset-risks/` - List all asset risks
- `POST /api/risk-registers/asset-risks/` - Create asset risk
- `GET /api/risk-registers/asset-risks/{id}/` - Get asset risk
- `PUT /api/risk-registers/asset-risks/{id}/` - Update asset risk
- `DELETE /api/risk-registers/asset-risks/{id}/` - Delete asset risk
- `POST /api/risk-registers/asset-risks/{id}/assess/` - Assess risk
- `POST /api/risk-registers/asset-risks/{id}/treat/` - Treat risk
- `POST /api/risk-registers/asset-risks/{id}/accept/` - Accept risk
- `POST /api/risk-registers/asset-risks/{id}/close/` - Close risk

### ThirdPartyRisk Endpoints

- `GET /api/risk-registers/third-party-risks/` - List all third party risks
- `POST /api/risk-registers/third-party-risks/` - Create third party risk
- `GET /api/risk-registers/third-party-risks/{id}/` - Get third party risk
- `PUT /api/risk-registers/third-party-risks/{id}/` - Update third party risk
- `DELETE /api/risk-registers/third-party-risks/{id}/` - Delete third party risk
- `POST /api/risk-registers/third-party-risks/{id}/assess/` - Assess risk
- `POST /api/risk-registers/third-party-risks/{id}/treat/` - Treat risk
- `POST /api/risk-registers/third-party-risks/{id}/accept/` - Accept risk
- `POST /api/risk-registers/third-party-risks/{id}/close/` - Close risk

### BusinessRisk Endpoints

- `GET /api/risk-registers/business-risks/` - List all business risks
- `POST /api/risk-registers/business-risks/` - Create business risk
- `GET /api/risk-registers/business-risks/{id}/` - Get business risk
- `PUT /api/risk-registers/business-risks/{id}/` - Update business risk
- `DELETE /api/risk-registers/business-risks/{id}/` - Delete business risk
- `POST /api/risk-registers/business-risks/{id}/assess/` - Assess risk
- `POST /api/risk-registers/business-risks/{id}/treat/` - Treat risk
- `POST /api/risk-registers/business-risks/{id}/accept/` - Accept risk
- `POST /api/risk-registers/business-risks/{id}/close/` - Close risk

### RiskTreatmentPlan Endpoints

- `GET /api/risk-registers/risk-treatment-plans/` - List all treatment plans
- `POST /api/risk-registers/risk-treatment-plans/` - Create treatment plan
- `GET /api/risk-registers/risk-treatment-plans/{id}/` - Get treatment plan
- `PUT /api/risk-registers/risk-treatment-plans/{id}/` - Update treatment plan
- `DELETE /api/risk-registers/risk-treatment-plans/{id}/` - Delete treatment plan
- `POST /api/risk-registers/risk-treatment-plans/{id}/activate/` - Activate plan
- `POST /api/risk-registers/risk-treatment-plans/{id}/complete/` - Complete plan
- `POST /api/risk-registers/risk-treatment-plans/{id}/abandon/` - Abandon plan

### RiskException Endpoints

- `GET /api/risk-registers/risk-exceptions/` - List all exceptions
- `POST /api/risk-registers/risk-exceptions/` - Create exception
- `GET /api/risk-registers/risk-exceptions/{id}/` - Get exception
- `PUT /api/risk-registers/risk-exceptions/{id}/` - Update exception
- `DELETE /api/risk-registers/risk-exceptions/{id}/` - Delete exception
- `POST /api/risk-registers/risk-exceptions/{id}/approve/` - Approve exception
- `POST /api/risk-registers/risk-exceptions/{id}/expire/` - Expire exception
- `POST /api/risk-registers/risk-exceptions/{id}/revoke/` - Revoke exception

## Filtering and Search

All endpoints support filtering, searching, and ordering:

- Filtering: `?lifecycle_state=assessed`
- Search: `?search=data breach`
- Ordering: `?ordering=-created_at`

## Next Steps

1. **Data Migration**: Migrate existing `core.RiskScenario` → risk registers
2. **Frontend Integration**: Update UI to use new endpoints
3. **Performance Testing**: Test with large datasets
4. **Documentation**: Add OpenAPI/Swagger documentation

## Related Documentation

- [DDD Infrastructure](../../domain/README.md)
- [Phase 4 Completion Guide](../../../../PHASE_4_RISK_REGISTERS_COMPLETE.md)
- [Refined Comprehensive Plan](../../../../REFINED_COMPREHENSIVE_PLAN.md)

