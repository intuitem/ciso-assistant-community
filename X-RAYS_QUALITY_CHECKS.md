# X-rays Quality Check Rules

X-rays is CISO Assistant's quality assurance feature that automatically analyzes risk assessments and compliance assessments to identify potential issues, inconsistencies, and areas requiring attention.

## Overview

The X-rays feature performs automated quality checks on:
- **Risk Assessments** - Including risk scenarios, applied controls, and risk acceptances
- **Compliance Assessments** - Including requirement assessments, applied controls, and evidence

An *issue* is one rule tripped on one object; the objects behind a rule are its *occurrences*. The word "finding" is avoided here, it names a different concept in the product (findings assessments).

Quality checks are categorized into three severity levels:
- **🐛 Errors** - Critical issues that need immediate attention
- **⚠️ Warnings** - Important issues that should be addressed
- **ℹ️ Info** - Informational notices and suggestions for improvement

## Access

X-rays can be accessed via:
- API endpoint: `GET /api/perimeters/quality_check/`
- Frontend route: `/x-rays`
- Feature must be enabled in global settings

## Risk Assessment Quality Checks

### Assessment-Level Checks

#### Info
| Rule ID | Message | Description |
|---------|---------|-------------|
| `riskAssessmentInProgress` | Risk assessment is still in progress | The assessment status is marked as IN_PROGRESS |
| `riskAssessmentNoAuthor` | No author assigned to this risk assessment | No users are assigned as authors to the assessment |

#### Warning
| Rule ID | Message | Description |
|---------|---------|-------------|
| `riskAssessmentEmpty` | RiskAssessment is empty. No risk scenario declared yet | The assessment has no risk scenarios created |

### Risk Scenario Checks

#### Error
| Rule ID | Message | Description |
|---------|---------|-------------|
| `riskScenarioNoResidualLevel` | Residual risk level has not been assessed. If no additional measures are applied, it should be at the same level as the current risk | Current level is assessed but residual level is not |
| `riskScenarioResidualHigherThanCurrent` | Residual risk level is higher than the current one | Residual risk level exceeds current risk level (illogical) |
| `riskScenarioResidualProbaHigherThanCurrent` | Residual risk probability is higher than the current one | Residual probability exceeds current probability (illogical) |
| `riskScenarioResidualImpactHigherThanCurrent` | Residual risk impact is higher than the current one | Residual impact exceeds current impact (illogical) |
| `riskScenarioResidualLoweredWithoutMeasures` | Residual risk level has been lowered without any specific measure | Risk reduced without applying any controls |
| `controlInBothLists` | [Control] appears in both existing and additional controls | A control cannot be both existing and additional |
| `existingControlNotActive` | [Control] is marked as an existing control but its status is not active | Existing controls must have "active" status |

#### Warning
| Rule ID | Message | Description |
|---------|---------|-------------|
| `riskScenarioNoCurrentLevel` | Current risk level has not been assessed | The scenario lacks current risk level assessment |
| `riskScenarioAcceptedNoAcceptance` | Risk accepted but no risk acceptance attached | Treatment is set to "accepted" without a formal risk acceptance |

### Applied Control Checks (Risk Assessments)

#### Error
| Rule ID | Message | Description |
|---------|---------|-------------|
| `appliedControlETAInPast` | ETA is in the past now. Consider updating its status or the date | The estimated completion date has passed |

#### Warning
| Rule ID | Message | Description |
|---------|---------|-------------|
| `appliedControlNoETA` | Does not have an ETA | Non-active control missing estimated time of arrival |
| `appliedControlNoEffort` | Does not have an estimated effort. This will help you for prioritization | Missing effort estimation |
| `appliedControlNoCost` | Does not have an estimated cost. This will help you for prioritization | Missing cost estimation |
| `appliedControlActiveNoEvidence` | Applied control is active but has no evidence attached | Active control with no evidence to back it |

#### Info
| Rule ID | Message | Description |
|---------|---------|-------------|
| `appliedControlNoLink` | Applied control does not have an external link attached. This will help you for follow-up | No external reference URL provided |

### Risk Acceptance Checks

#### Error
| Rule ID | Message | Description |
|---------|---------|-------------|
| `riskAcceptanceExpired` | Acceptance has expired. Consider updating the status or the date | The expiry date has passed |

#### Warning
| Rule ID | Message | Description |
|---------|---------|-------------|
| `riskAcceptanceNoExpiryDate` | Acceptance has no expiry date | Risk acceptance lacks an expiration date |

## Compliance Assessment Quality Checks

### Assessment-Level Checks

#### Info
| Rule ID | Message | Description |
|---------|---------|-------------|
| `complianceAssessmentInProgress` | Compliance assessment is still in progress | The assessment status is marked as IN_PROGRESS |
| `complianceAssessmentNoAuthor` | No author assigned to this compliance assessment | No users are assigned as authors to the assessment |

### Requirement Assessment Checks

#### Warning
| Rule ID | Message | Description |
|---------|---------|-------------|
| `requirementAssessmentCompliantNoEvidence` | Requirement assessment is compliant but has no evidence attached | Assessable requirement marked compliant without supporting evidence |
| `requirementAssessmentNoAppliedControl` | Requirement assessment result is compliant or partially compliant with no applied control applied | Compliance claimed without any controls applied |

### Applied Control Checks (Compliance Assessments)

#### Info
| Rule ID | Message | Description |
|---------|---------|-------------|
| `appliedControlNoReferenceControl` | Applied control has no reference control selected | Control lacks linkage to a reference control framework |

#### Warning
| Rule ID | Message | Description |
|---------|---------|-------------|
| `appliedControlActiveNoEvidence` | Applied control is active but has no evidence attached | Active control with no evidence to back it |

### Evidence Checks

#### Warning
| Rule ID | Message | Description |
|---------|---------|-------------|
| `evidenceNoFile` | Evidence has no file or link uploaded | Evidence object exists but contains no actual files or URLs |

## Implementation Details

### Backend Implementation

Quality checks are implemented in `backend/core/models.py`:
- `RiskAssessment.quality_check()` - Line 3838
- `ComplianceAssessment.quality_check()` - Line 5085

Both methods return a dictionary with:
```python
{
    "errors": [],      # List of error issues
    "warnings": [],    # List of warning issues
    "info": [],        # List of info issues
    "count": 0         # Total number of issues
}
```

Each issue contains:
- `msg` - Human-readable message (translated)
- `msgid` - Message identifier for i18n
- `obj_type` - Type of object (e.g., "riskscenario", "appliedcontrol")
- `object` - Compact object built by `_issue_object()`: `id`, `name`, plus the few
  metadata fields the X-rays table shows as columns. The full serialized object is
  deliberately *not* shipped, it used to be repeated for every issue raised on it.
- `link` - Optional direct link to edit the object (format: `model-name/id`)

Metadata carried per object type:

| `obj_type` | Extra fields |
|---|---|
| `appliedcontrol` | `status`, `eta`, `priority` |
| `riskscenario` | `ref_id`, `treatment` |
| `requirementassessment` | `result`, `status` |
| `riskacceptance` | `state`, `expiry_date` |
| `evidence` | none |
| `risk_assessment`, `complianceassessment` | `status` |

### API Implementation

The PerimeterViewSet exposes quality check data via:
- `GET /api/perimeters/quality_check/` - All perimeters (line 477 in views.py)
- `GET /api/perimeters/{id}/quality_check/` - Specific perimeter (line 514 in views.py)

### Frontend Implementation

The X-rays page is implemented in:
- `frontend/src/routes/(app)/(internal)/x-rays/+page.svelte`
- `frontend/src/routes/(app)/(internal)/x-rays/+page.server.ts`

Shared components live in `frontend/src/lib/components/XRays/`:
- `utils.ts` - severity table, per-`obj_type` column config, aggregation
- `AssessmentIssues.svelte` - one assessment, collapsed by default
- `IssueTable.svelte` - occurrences of one rule, paginated client-side

Features:
- Groups issues by domain, then assessment, then rule (msgid)
- Separate tabs for compliance and risk assessments
- Severity filter to hide whole tiers
- Everything collapsed by default; assessments with no issue are not rendered
- Occurrences shown in a paginated table with per-type metadata columns
- Direct links to edit affected objects
- Color-coded badges (red=errors, yellow=warnings, blue=info)

## Best Practices

1. **Regular Review** - Check X-rays regularly to maintain data quality
2. **Fix Errors First** - Address critical errors before warnings or info items
3. **Evidence Documentation** - Always attach evidence files or links to compliant requirements
4. **Control Planning** - Set ETAs, effort, and cost estimates for better prioritization
5. **Risk Logic** - Ensure residual risk is never higher than current risk
6. **Acceptance Management** - Set expiry dates on all risk acceptances
7. **Status Updates** - Keep control statuses current when ETAs pass

## Feature Flag

X-rays can be enabled/disabled via the global settings feature flags. The feature is controlled by the `x-rays` flag in the system configuration.
