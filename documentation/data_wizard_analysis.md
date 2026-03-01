# Data Wizard Analysis: Supported Models and Fields

## Overview

The Data Wizard is located in `/backend/data_wizard/`. It supports importing data from Excel/CSV files into CISO Assistant.

## Supported Model Types

The Data Wizard defines the following `ModelType` enum for supported imports:

| Model Type | Import Method | Status |
|------------|---------------|--------|
| `Asset` | Single sheet CSV/Excel | **Supported** |
| `AppliedControl` | Single sheet CSV/Excel | **Supported** |
| `Perimeter` | Single sheet CSV/Excel | **Supported** |
| `User` | Single sheet CSV/Excel | **Supported** |
| `ComplianceAssessment` | Single sheet CSV/Excel | **Supported** |
| `FindingsAssessment` | Single sheet CSV/Excel | **Supported** |
| `RiskAssessment` | Single sheet CSV/Excel | **Supported** |
| `ElementaryAction` | Single sheet CSV/Excel | **Supported** |
| `ReferenceControl` | Single sheet CSV/Excel | **Supported** |
| `Threat` | Single sheet CSV/Excel | **Supported** |
| `Processing` | Single sheet CSV/Excel | **Supported** |
| `Folder` | Single sheet CSV/Excel | **Supported** |
| `Evidence` | Single sheet CSV/Excel | **Supported** |
| `Policy` | Single sheet CSV/Excel | **Supported** |
| `SecurityException` | Single sheet CSV/Excel | **Supported** |
| `Incident` | Single sheet CSV/Excel | **Supported** |
| `TPRM` | Multi-sheet Excel (Entities, Solutions, Contracts) | **Supported** |
| `EbiosRMStudyARM` | Multi-sheet Excel (ARM format) | **Supported** |
| `EbiosRMStudyExcel` | Multi-sheet Excel (Native export format) | **Supported** |

---

## Detailed Field Mappings by Model

### 1. Asset (`AssetRecordConsumer`)

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `ref_id` | No | Reference ID |
| `name` | **Yes** | Asset name |
| `type` | No | Mapped: primary/PR, support/SP (defaults to "SP") |
| `domain` | No | Folder name lookup |
| `description` | No | |
| `business_value` | No | Free text |
| `reference_link` | No | URL (also accepts `link`) |
| `observation` | No | Free text |
| `parent_assets` | No | Comma/pipe-separated ref_ids (linked in second pass) |
| `filtering_labels` | No | Pipe- or comma-separated label names (created if missing) |

**Missing Fields from Model:**
| Field | Type | Priority |
|-------|------|----------|
| `owner` | M2M Actor | Medium |
| `asset_class` | FK AssetClass | Medium |
| `security_objectives` | JSONField | Low (complex) |
| `disaster_recovery_objectives` | JSONField | Low (complex) |
| DORA-related fields | Various | Low |

---

### 2. AppliedControl (`AppliedControlRecordConsumer`)

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `ref_id` | No | Reference ID |
| `name` | **Yes** | Control name |
| `description` | No | |
| `category` | No | |
| `domain` | No | Folder lookup |
| `status` | No | Defaults to "to_do" |
| `priority` | No | Integer (1-4) |
| `csf_function` | No | Defaults to "govern" |
| `eta` | No | Date (YYYY-MM-DD) |
| `expiry_date` | No | Date (YYYY-MM-DD) |
| `start_date` | No | Date (YYYY-MM-DD) |
| `link` | No | URL |
| `effort` | No | Mapped: XS, S, M, L, XL (or full names) |
| `control_impact` | No | Integer (1-5), also accepts `impact` |
| `reference_control` | No | Lookup by ref_id (also accepts `reference_control_ref_id`) |
| `filtering_labels` | No | Pipe- or comma-separated label names (created if missing) |
| `observation` | No | Free text |

**Missing Fields from Model:**
| Field | Type | Priority |
|-------|------|----------|
| `cost` | JSONField | Medium (complex structure) |
| `owner` | M2M Actor | Medium |
| `evidences` | M2M | Medium |
| `assets` | M2M | Medium |

---

### 3. Evidence (`EvidenceRecordConsumer`)

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `name` | **Yes** | Evidence name |
| `description` | No | |
| `ref_id` | No | Reference ID |
| `domain` | No | Folder lookup |
| `filtering_labels` | No | Pipe- or comma-separated label names (created if missing) |

**Missing Fields from Model:**
| Field | Type | Priority |
|-------|------|----------|
| `attachment` | FileField | Medium |
| `link` | URLField | High |
| `expiry_date` | DateField | Medium |
| `owner` | FK User | Medium |

---

### 4. User (`UserRecordConsumer`)

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `email` | **Yes** | User email |
| `first_name` | No | |
| `last_name` | No | |

**Missing Fields from Model:**
| Field | Type | Priority |
|-------|------|----------|
| `is_active` | BooleanField | High |
| `is_superuser` | BooleanField | Low |
| `mailing_list_consent` | BooleanField | Low |
| `preferences` | JSONField | Low |

---

### 5. Perimeter (`PerimeterRecordConsumer`)

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `name` | **Yes** | Perimeter name |
| `domain` | No | Folder lookup |
| `ref_id` | No | Reference ID |
| `description` | No | |
| `status` | No | |

**Missing Fields from Model:**
| Field | Type | Priority |
|-------|------|----------|
| `reference_link` | URLField | Medium |
| `filtering_labels` | M2M | Medium |

---

### 6. Threat (`ThreatRecordConsumer`)

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `name` | **Yes** | Threat name |
| `description` | No | |
| `domain` | No | Folder lookup |
| `ref_id` | No | Reference ID |

**Missing Fields from Model:**
| Field | Type | Priority |
|-------|------|----------|
| `annotation` | TextField | Medium |
| `provider` | CharField | Low |
| `is_published` | BooleanField | Low |
| i18n fields | Various | Low |

---

### 7. ReferenceControl (`ReferenceControlRecordConsumer`)

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `name` | **Yes** | Control name |
| `description` | No | |
| `ref_id` | No | Reference ID |
| `domain` | No | Folder lookup |
| `category` | No | Mapped: policy, process, technical, physical, procedure |
| `function` | No | Maps to `csf_function`: govern, identify, protect, detect, respond, recover |

**Missing Fields from Model:**
| Field | Type | Priority |
|-------|------|----------|
| `annotation` | TextField | Medium |
| `provider` | CharField | Low |
| `typical_evidence` | TextField | Medium |
| `implementation_groups` | ArrayField | Low |
| i18n fields | Various | Low |

---

### 8. FindingsAssessment (`FindingsAssessmentRecordConsumer`)

**Supported Fields (for Finding):**
| Field | Required | Notes |
|-------|----------|-------|
| `name` | **Yes** | Finding name |
| `description` | No | |
| `ref_id` | No | Reference ID |
| `status` | No | |
| `severity` | No | Mapped: info, low, medium, high, critical |
| `filtering_labels` | No | Pipe- or comma-separated values (created if missing) |
| `eta` | No | Date (YYYY-MM-DD) |
| `due_date` | No | Date (YYYY-MM-DD) |
| `priority` | No | Integer (1-4: P1-P4) |
| `observation` | No | Free text |

**Missing Fields from Model:**
| Field | Type | Priority |
|-------|------|----------|
| `owner` | M2M Actor | High |
| `applied_controls` | M2M | Medium |
| `evidences` | M2M | Medium |
| `threats` | M2M | Medium |
| `vulnerabilities` | M2M | Medium |

---

### 9. ComplianceAssessment

**Behavior:** Creates a new ComplianceAssessment and updates RequirementAssessments

**Supported Fields (for RequirementAssessment):**
| Field | Required | Notes |
|-------|----------|-------|
| `ref_id` or `urn` | **Yes** | Used to match requirements |
| `assessable` | No | Skips non-assessable items |
| `compliance_result` | No | Maps to `result` |
| `requirement_progress` | No | Maps to `status` |
| `observations` | No | Maps to `observation` |
| `implementation_score` | No | Maps to `score` |
| `documentation_score` | No | |
| `score` | No | Single-score mode (when no documentation_score) |
| `Q: <question text>` | No | Flattened questionnaire answers (see below) |

**Dynamic Questionnaire Support (Q: columns):**

For frameworks using dynamic questionnaires, the export/import supports flattened question columns:

- **Export:** Each question appears as a column header `Q: <question text>`. Cell values are human-readable choice texts. Multiple-choice answers are pipe-separated (`choice1 | choice2`). Text/date answers appear as-is.
- **Import:** The importer matches `Q: ` column headers to the requirement's question texts, reverse-maps choice values to URNs, and builds the `answers` JSON. The existing `compute_score_and_result()` then automatically computes score and compliance result from the imported answers.
- Columns only appear when the framework has questions. Non-questionnaire frameworks are unaffected.
- Conditional question visibility (`depends_on`) is handled automatically during score/result computation.

**Missing RequirementAssessment Fields:**
| Field | Type | Priority |
|-------|------|----------|
| `mapping_inference` | CharField | Low |
| `selected` | BooleanField | Medium |
| `eta` | DateField | High |
| `due_date` | DateField | High |
| `owner` | FK User | High |
| `reviewer` | FK User | Medium |
| `applied_controls` | M2M | High |
| `evidences` | M2M | High |

---

### 10. RiskAssessment

**Behavior:** Creates RiskAssessment with RiskScenarios

**Supported Fields (for RiskScenario):**
| Field | Required | Notes |
|-------|----------|-------|
| `ref_id` | No | Reference ID |
| `name` | **Yes** | Scenario name |
| `description` | No | |
| `inherent_impact` | No | |
| `inherent_proba` | No | |
| `current_impact` | No | |
| `current_proba` | No | |
| `residual_impact` | No | |
| `residual_proba` | No | |
| `existing_applied_controls` | No | Newline-separated, creates/finds controls |
| `additional_controls` | No | Newline-separated |
| `treatment` | No | Defaults to "open" |
| `filtering_labels` | No | Pipe- or comma-separated label names (created if missing, set post-save) |

**Missing RiskScenario Fields:**
| Field | Type | Priority |
|-------|------|----------|
| `strength_of_knowledge` | CharField | Medium |
| `justification` | TextField | Medium |
| `owner` | FK User | High |
| `threats` | M2M | High |
| `assets` | M2M | High |
| `vulnerabilities` | M2M | Medium |

---

### 11. ElementaryAction

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `name` | **Yes** | Action name |
| `description` | No | |
| `ref_id` | No | Reference ID |
| `domain` | No | Folder lookup |
| `attack_stage` | No | Mapped FR/EN: know/connaitre→0, enter/pénétrer→1, discover/trouver→2, exploit/exploiter→3 |
| `icon` | No | Mapped: server, computer, cloud, file, etc. |

**Missing Fields from Model:**
| Field | Type | Priority |
|-------|------|----------|
| `threat` | FK Threat | Medium |

---

### 12. Processing (Privacy)

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `name` | **Yes** | Processing name |
| `description` | No | |
| `ref_id` | No | Reference ID |
| `domain` | No | Folder lookup |
| `status` | No | Supports display value mapping |
| `dpia_required` | No | Boolean |
| `dpia_reference` | No | |
| `processing_nature` | No | Comma-separated names |
| `assigned_to` | No | Comma-separated emails |
| `labels` | No | Maps to `filtering_labels`, comma-separated |

**Missing Fields from Model:**
| Field | Type | Priority |
|-------|------|----------|
| `author` | FK User | Medium |
| `information_channel` | TextField | Low |
| `usage_channel` | TextField | Low |
| `has_sensitive_personal_data` | BooleanField | High |
| `associated_controls` | M2M | Medium |
| `evidences` | M2M | Medium |
| `perimeters` | M2M | Medium |

---

### 13. Folder

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `name` | **Yes** | Folder name |
| `description` | No | |
| `domain` | No | Maps to `parent_folder` (name lookup) |

**Missing Fields from Model:**
| Field | Type | Priority |
|-------|------|----------|
| `content_type` | CharField | Low |
| `builtin` | BooleanField | Low |
| `hide_in_selects` | BooleanField | Low |

---

### 14. Policy (`PolicyRecordConsumer`)

Policy is a proxy model of AppliedControl with `category='policy'`.

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `ref_id` | No | Reference ID |
| `name` | **Yes** | Policy name |
| `description` | No | |
| `domain` | No | Folder name lookup |
| `status` | No | Defaults to "to_do" |
| `priority` | No | Integer (1-4) |
| `csf_function` | No | Defaults to "govern" |
| `eta` | No | Date (YYYY-MM-DD) |
| `expiry_date` | No | Date (YYYY-MM-DD) |
| `link` | No | URL |
| `effort` | No | XS, S, M, L, XL |
| `filtering_labels` | No | Pipe- or comma-separated label names (created if missing) |

**Missing Fields from Model:**
| Field | Type | Priority |
|-------|------|----------|
| `owner` | M2M Actor | High |
| `evidences` | M2M | Medium |
| `reference_control` | FK | Medium |
| `cost` | IntegerField | Low |
| `start_date` | DateField | Low |

---

### 15. SecurityException (`SecurityExceptionRecordConsumer`)

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `ref_id` | No | Reference ID |
| `name` | **Yes** | Exception name |
| `description` | No | |
| `domain` | No | Folder name lookup |
| `severity` | No | Mapped: undefined, info, low, medium, high, critical |
| `status` | No | Mapped: draft, in_review, approved, resolved, expired, deprecated |
| `expiration_date` | No | Date (YYYY-MM-DD) |
| `observation` | No | Text observations |

**Missing Fields from Model:**
| Field | Type | Priority |
|-------|------|----------|
| `owners` | M2M Actor | High |
| `approver` | FK User | High |
| `requirement_assessments` | M2M | Medium |
| `applied_controls` | M2M | Medium |
| `assets` | M2M | Medium |
| `is_published` | BooleanField | Low |

---

### 16. Incident (`IncidentRecordConsumer`)

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `ref_id` | No | Reference ID |
| `name` | **Yes** | Incident name |
| `description` | No | |
| `domain` | No | Folder name lookup |
| `severity` | No | Mapped: critical/sev1(1), major/sev2(2), moderate/sev3(3), minor/sev4(4), low/sev5(5), unknown(6) |
| `status` | No | Mapped: new, ongoing, resolved, closed, dismissed |
| `detection` | No | Mapped: internal/internally_detected, external/externally_detected |
| `link` | No | URL |
| `reported_at` | No | DateTime |
| `filtering_labels` | No | Pipe- or comma-separated label names (created if missing) |

**Missing Fields from Model:**
| Field | Type | Priority |
|-------|------|----------|
| `owners` | M2M Actor | High |
| `threats` | M2M | High |
| `assets` | M2M | High |
| `entities` | M2M | Medium |
| `qualifications` | M2M Terminology | Medium |
| `is_published` | BooleanField | Low |

---

### 17. TPRM (Multi-sheet Import)

#### Entities Sheet

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `ref_id` | **Yes** | Reference ID |
| `name` | **Yes** | Entity name |
| `description` | No | |
| `mission` | No | |
| `domain` | No | Folder lookup |
| `country` | No | |
| `currency` | No | |
| `dependency` | No | Maps to `default_dependency` |
| `penetration` | No | Maps to `default_penetration` |
| `maturity` | No | Maps to `default_maturity` |
| `trust` | No | Maps to `default_trust` |
| `lei` | No | Maps to `legal_identifiers.lei` |
| `euid` | No | Maps to `legal_identifiers.euid` |
| `duns` | No | Maps to `legal_identifiers.duns` |
| `vat` | No | Maps to `legal_identifiers.vat` |
| `parent_entity_ref_id` | No | Second pass relationship |

**Missing Entity Fields:**
| Field | Type | Priority |
|-------|------|----------|
| `reference_link` | URLField | Medium |
| `builtin` | BooleanField | Low |
| `is_active` | BooleanField | Medium |
| `owned_folders` | M2M | Low |
| `relationship` | CharField | Medium |
| DORA-specific fields | Various | Medium |

#### Solutions Sheet

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `ref_id` | **Yes** | Reference ID |
| `name` | **Yes** | Solution name |
| `description` | No | |
| `provider_entity_ref_id` | **Yes** | Provider entity reference |
| `criticality` | No | |

**Missing Solution Fields:**
| Field | Type | Priority |
|-------|------|----------|
| `recipient_entity` | FK | Medium |
| `is_active` | BooleanField | Medium |
| `reference_link` | URLField | Medium |
| `owner` | FK User | Medium |
| `assets` | M2M | High |
| `dora_ict_service_type` | CharField | Medium |
| `filtering_labels` | M2M | Medium |
| All other DORA fields | Various | Medium |

#### Contracts Sheet

**Supported Fields:**
| Field | Required | Notes |
|-------|----------|-------|
| `ref_id` | **Yes** | Reference ID |
| `name` | **Yes** | Contract name |
| `description` | No | |
| `provider_entity_ref_id` | **Yes** | Provider entity reference |
| `domain` | No | Folder lookup |
| `solution_ref_id` | No | Solution reference |
| `status` | No | |
| `start_date` | No | |
| `end_date` | No | |
| `annual_expense` | No | |
| `currency` | No | |

**Missing Contract Fields:**
| Field | Type | Priority |
|-------|------|----------|
| `beneficiary_entity` | FK | Medium |
| `evidences` | M2M | Medium |
| `owner` | FK User | Medium |
| `overarching_contract` | FK | Low |
| All DORA-related fields | Various | Medium |
| `filtering_labels` | M2M | Medium |

---

### 18. EbiosRMStudyARM (ARM Format Import)

**Creates the following objects:**
- EbiosRMStudy (name, description, risk_matrix, folder)
- Assets (primary and supporting, with parent relationships)
- AppliedControls
- FearedEvents (linked to assets)
- RoTo Couples (with Terminology creation for risk_origin)
- Stakeholders (with Entity and Terminology creation)
- StrategicScenarios (linked to RoTo)
- AttackPaths (linked to StrategicScenario)
- ElementaryActions

**Workshop Progress Tracking:** Updates study.meta for workshop steps 1-4

---

### 19. EbiosRMStudyExcel (Native Export Format Import)

**Additional objects created beyond ARM:**
- OperationalScenarios
- OperatingModes (with elementary action linking)

---


## 20. Vulnerability

| Field | Type | Required | Note |
|-------|------|---------|-------|
| `ref_id`      | string | No  ||
| `name`        | string | yes ||
| `description` | string | No  ||
|`status`       | string | No  | The list of the possible statuses below |
| `severity`    | string | No  | The list of the possible severities below |
| `filtering_label` | list | No | List of labels, newline-separated |
| `assets`      | list   | No | List of the named of the related assets, newline-separated |
| `applied_controls` | list | No | List of the name of the related applied controls, newline-separated |
| `security_exceptions`| list | No | List of the name of the related security exceptions, newline-separated |

**Vulnerability's status**
* Potential
* Exploitable
* Mitigated
* Fixed
* Not exploitable
* Unaffected

**Vulnerability's severity**
* Information
* Low
* Medium
* High
* Critical


## Models NOT Supported by Data Wizard

### Core App (`core/models.py`)

| Model | Status | Priority to Add |
|-------|--------|-----------------|
| StoredLibrary | Not supported | Low (system managed) |
| LoadedLibrary | Not supported | Low (system managed) |
| Terminology | Not supported | Low (created via EBIOS) |
| RiskMatrix | Not supported | Medium |
| Framework | Not supported | Low (library system) |
| RequirementNode | Not supported | Low (library system) |
| RequirementMappingSet | Not supported | Low |
| RequirementMapping | Not supported | Low |
| SecurityException | **Supported** | Done |
| AssetCapability | Not supported | Low |
| AssetClass | Not supported | Low |
| EvidenceRevision | Not supported | Low (system managed) |
| Incident | **Supported** | Done |
| TimelineEntry | Not supported | Low |
| OrganisationIssue | Not supported | Medium |
| OrganisationObjective | Not supported | Medium |
| Policy | **Supported** | Done |
| HistoricalMetric | Not supported | Low |
| Campaign | Not supported | Medium |
| RiskAcceptance | **Not supported** | **High** |
| TaskTemplate | Not supported | Medium |
| TaskNode | Not supported | Low |
| ValidationFlow | Not supported | Low |
| FlowEvent | Not supported | Low |
| Team | Not supported | Medium |
| Actor | Not supported | Medium |
| FilteringLabel | Not supported | Low (read-only lookup) |

### Resilience App (`resilience/models.py`)

| Model | Status | Priority to Add |
|-------|--------|-----------------|
| BusinessImpactAnalysis | **Not supported** | **High** |
| AssetAssessment | **Not supported** | **High** |
| EscalationThreshold | Not supported | Medium |

### EBIOS RM App (`ebios_rm/models.py`)

| Model | Direct Import | Via EBIOS Study Import | Priority |
|-------|---------------|------------------------|----------|
| EbiosRMStudy | Not directly | Yes (ARM & Excel) | Low |
| FearedEvent | Not directly | Yes | Low |
| RoTo | Not directly | Yes | Low |
| Stakeholder | Not directly | Yes | Low |
| StrategicScenario | Not directly | Yes | Low |
| AttackPath | Not directly | Yes | Low |
| ElementaryAction | Yes (single) | Yes (via study) | Done |
| OperatingMode | Not directly | Yes (Excel only) | Low |
| OperationalScenario | Not directly | Yes (Excel only) | Low |
| KillChain | **Not supported** | **Not supported** | Medium |

### TPRM App (`tprm/models.py`)

| Model | Status | Priority to Add |
|-------|--------|-----------------|
| Entity | Yes (via TPRM import) | Done |
| EntityAssessment | **Not supported** | **High** |
| Representative | **Not supported** | **High** |
| Solution | Yes (via TPRM import) | Done |
| Contract | Yes (via TPRM import) | Done |

### Privacy App (`privacy/models.py`)

| Model | Status | Priority to Add |
|-------|--------|-----------------|
| ProcessingNature | Not supported (lookup only) | Low |
| Processing | Yes (single sheet) | Done |
| Purpose | **Not supported** | **High** |
| PersonalData | **Not supported** | **High** |
| DataSubject | **Not supported** | **High** |
| DataRecipient | **Not supported** | **Medium** |
| DataContractor | **Not supported** | **Medium** |
| DataTransfer | **Not supported** | **Medium** |
| RightRequest | **Not supported** | **High** |
| DataBreach | **Not supported** | **High** |

### IAM App (`iam/models.py`)

| Model | Status | Priority to Add |
|-------|--------|-----------------|
| Folder | Yes (single sheet) | Done |
| UserGroup | Not supported | Medium |
| User | Yes (limited fields) | Partial |
| Role | Not supported | Low |
| RoleAssignment | Not supported | Medium |
| PersonalAccessToken | Not supported | Low |

---

## Summary Statistics

| Category | Count |
|----------|-------|
| **Total Models Identified** | ~70 |
| **Models with Direct Import Support** | 16 |
| **Models with Indirect Import Support** | ~12 (via EBIOS/TPRM) |
| **Models NOT Supported** | ~42 |

---

## Recommendations for Expansion

### High Priority (Core GRC Functionality)

1. **RiskAcceptance** - Risk management workflow completion
2. **Vulnerability** - Vulnerability tracking
3. ~~**Incident**~~ - ✅ Now supported
4. ~~**SecurityException**~~ - ✅ Now supported
5. ~~**Policy**~~ - ✅ Now supported

### High Priority (TPRM Completion)

6. **Representative** - Contact information for entities
7. **EntityAssessment** - Third-party risk assessments

### High Priority (Privacy/GDPR Compliance)

7. **Purpose** - Processing purposes
8. **PersonalData** - Data categories
9. **DataSubject** - Data subject categories
10. **DataBreach** - Breach notification management
11. **RightRequest** - Data subject rights

### High Priority (Resilience)

12. **BusinessImpactAnalysis** - BIA import
13. **AssetAssessment** - Asset assessments for BIA

### Medium Priority

14. **Team** - Organization structure
15. **Actor** - User profiles/personas
16. **UserGroup** - Group management
17. **RoleAssignment** - RBAC import
18. **Campaign** - Assessment campaigns

### Field Expansion Priority

For existing supported models, prioritize adding:
1. `owner` field (FK to User) - across all models
2. `eta` and `due_date` fields - for task tracking
3. ~~`filtering_labels` (M2M) - for organization~~ ✅ Added to Asset, AppliedControl, Evidence, Finding, Policy, Incident, RiskScenario
4. `applied_controls` and `evidences` (M2M) - for linking
5. `threats` and `assets` (M2M) - for RiskScenario
