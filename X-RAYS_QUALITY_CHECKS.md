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

Every rule below is skipped when the requirement is not assessable, when it falls
outside the audit's selected implementation groups, or when the audit hides a
field the rule reads — an audit that hides `status` or `result` cannot be judged
on it.

Expiry is decided on the date rather than the status: `mark_expired_evidences`
only runs under Huey, and applied controls are never marked expired at all
(CA-1869).

#### Error
| Rule ID | Message | Description |
|---------|---------|-------------|
| `requirementAssessmentControlExpired` | Requirement assessment relies on an applied control past its expiry date | Compliance claimed on a control that has lapsed |

#### Warning
| Rule ID | Message | Description |
|---------|---------|-------------|
| `requirementAssessmentCompliantNoEvidence` | Requirement assessment is compliant but has no evidence attached | Assessable requirement marked compliant without supporting evidence |
| `requirementAssessmentNoAppliedControl` | Requirement assessment result is compliant or partially compliant with no applied control applied | Compliance claimed without any controls applied |
| `requirementAssessmentCompliantNoActiveControl` | Requirement assessment is compliant but none of its applied controls is active | Controls exist, but nothing is live yet |
| `requirementAssessmentControlDeprecatedOrDegraded` | Requirement assessment relies on a deprecated or degraded applied control | Compliance rests on a control that has been retired or is only partly working |
| `requirementAssessmentPartialNoStartedControl` | Requirement assessment is partially compliant but none of its applied controls has started | "Partially compliant" with nothing under way is non-compliance with a plan |
| `requirementAssessmentControlEtaMissed` | Requirement assessment depends on an applied control whose ETA has passed | The remediation this requirement depends on has slipped |
| `requirementAssessmentEvidenceExpired` | Every evidence supporting this requirement assessment has expired | Nothing current substantiates the verdict |
| `requirementAssessmentEvidenceRejected` | Requirement assessment relies on an evidence that was rejected | A reviewer already refused this evidence |
| `requirementAssessmentEvidenceAllDraft` | Requirement assessment is compliant but none of its evidence has left draft | Nothing supporting the verdict has been reviewed |
| `requirementAssessmentNotApplicableNoJustification` | Requirement assessment is not applicable with no justification | An external auditor asks for this one every time |
| `requirementAssessmentDoneNotAssessed` | Requirement assessment is marked done but has no result | Marked finished with no verdict recorded |

#### Info
| Rule ID | Message | Description |
|---------|---------|-------------|
| `requirementAssessmentNonCompliantActiveControls` | Requirement assessment is non-compliant while all its applied controls are active | Either the verdict or the control statuses are out of date |
| `requirementAssessmentNonCompliantNoObservation` | Requirement assessment is non-compliant with no observation | The gap is recorded without saying what it is |
| `requirementAssessmentPartialNoObservation` | Requirement assessment is partially compliant with no observation | What is missing is not written down |
| `requirementAssessmentResultWithoutProgress` | Requirement assessment has a result while still marked to do | The progress status contradicts the verdict |

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
- `RiskAssessment.quality_check()`
- `ComplianceAssessment.quality_check()`
- `RequirementAssessment.quality_check()`, also exposed as
  `GET /requirement-assessments/{id}/quality_check/`

The requirement rules live on `RequirementAssessment`; the audit-level check only
decides which requirements are in scope and calls the same rules, so a finding
cannot differ between the two surfaces. They are evaluated against a
`RequirementAssessmentQualityContext` resolved in three queries for the whole
audit — the rules themselves issue none, so the query count does not grow with
the number of requirements.

All three methods return a dictionary with:
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
  metadata fields the X-rays table shows as columns.
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
- Domain search, sort by severity or name, expand / collapse all
- Everything collapsed by default; domains and assessments with no issue are not rendered
- A domain's tabs mount only once it is opened, so hundreds of domains stay cheap
- Occurrences shown in a paginated, searchable table with per-type metadata columns
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
