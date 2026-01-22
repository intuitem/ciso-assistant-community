# RMF Operations Bounded Context

## Overview

The RMF Operations bounded context manages STIG checklists, systems, vulnerabilities, scoring, and RMF-specific workflows for Risk Management Framework (RMF) operations.

This context integrates with:
- **ControlLibrary**: Links STIG vulnerabilities to controls via STIG IDs and CCI mappings
- **Compliance**: Links system-level compliance audits and findings to vulnerabilities
- **AssetAndService**: Links assets to system groups

## Phase 0 Status

✅ **Completed**:
- Bounded context structure created
- Domain events defined
- App registered in Django settings
- URL routing configured
- XML parsing dependency (lxml) added

## Architecture

### Planned Aggregates (Phase 1+)

1. **SystemGroup** - System packages (groups of checklists/assets)
2. **StigChecklist** - STIG checklist (CKL file)
3. **VulnerabilityFinding** - Vulnerability finding within a checklist
4. **ChecklistScore** - Scoring/statistics for a checklist
5. **StigTemplate** - STIG template for creating checklists

### Planned Associations (Phase 4+)

1. **NessusScan** - Nessus ACAS scan results
2. **CciMapping** - CCI to NIST control mapping

### Domain Events

All domain events are defined in `domain_events.py`:
- SystemGroup events (Created, Activated, Archived, etc.)
- StigChecklist events (Created, Imported, Exported, etc.)
- VulnerabilityFinding events (Created, StatusChanged, SeverityOverridden, etc.)
- ChecklistScore events (Calculated, Updated, SystemAggregated)
- StigTemplate events (Created, ChecklistCreatedFromTemplate)
- NessusScan events (Uploaded, Processed)

## Quick Start

### 1. Install Dependencies

```bash
cd backend
poetry install
```

This will install `lxml` for XML parsing of CKL files.

### 2. Register the App

The app is already registered in `ciso_assistant/settings.py`:
```python
INSTALLED_APPS = [
    # ...
    "core.bounded_contexts.rmf_operations",
    # ...
]
```

### 3. Run Migrations (Phase 1)

Migrations will be created in Phase 1 when aggregates are implemented:
```bash
poetry run python manage.py makemigrations core.bounded_contexts.rmf_operations
poetry run python manage.py migrate core.bounded_contexts.rmf_operations
```

### 4. Access API (Phase 1)

API endpoints will be available at:
- `/api/rmf/systems/` - System groups
- `/api/rmf/checklists/` - STIG checklists
- `/api/rmf/vulnerabilities/` - Vulnerability findings
- `/api/rmf/templates/` - STIG templates

## Next Steps

**Phase 1: Foundation** (Months 1-3)
- [ ] Create SystemGroup aggregate
- [ ] Create StigChecklist aggregate
- [ ] Create VulnerabilityFinding aggregate
- [ ] Implement CKL file parser
- [ ] Implement CKL file serializer
- [ ] Create basic CRUD APIs
- [ ] Write unit tests

## Related Documentation

- [RMF Integration Plan](../../../../CISO_ASSISTANT_RMF_INTEGRATION_PLAN.md)
- [OpenRMF DDL Analysis](../../../../OPENRMF_DDL_ANALYSIS.md)
- [OpenRMF UI/UX Field Trace](../../../../OPENRMF_UI_UX_FIELD_TRACE.md)
- [DDD Infrastructure](../../domain/README.md)

