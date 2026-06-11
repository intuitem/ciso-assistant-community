# Feature flags

Feature flags turn whole product areas on or off. They're how you tailor the navigation and the surface area to what your team actually uses, and how you keep experimental or specialised features out of sight until you want them.

Flags affect what's visible in the sidebar, what appears in CRUD pages, and which permissions are even relevant. They do **not** delete any underlying data — turning a flag off hides the feature; turning it back on restores the UI as it was.

## Operations

- **xrays** — the X-rays inconsistency-detection page.
- **incidents** — incident management.
- **tasks** — the task-management module (one-off and recurring tasks).
- **control_plan** — the consolidated control-plan view across applied controls.

## Governance

- **risk_acceptances** — the risk-acceptance workflow.
- **exceptions** — security-exception tracking.
- **follow_up** — findings assessments (follow-up).
- **validation_flows** — configurable approval workflows that mirror internal review or management-approval processes, attached to objects whose state changes warrant sign-off. _Default off._
- **organisation_issues** — context register: issues affecting the organisation.
- **organisation_objectives** — context register: organisational objectives.
- **policy_documents** — the dedicated Policies surface (a filtered view of applied controls).

## Risk

- **ebiosrm** — the EBIOS RM module.
- **scoring_assistant** — the OWASP-based scoring assistant.
- **vulnerabilities** — vulnerability tracking.
- **quantitative_risk_studies** — Monte-Carlo quantitative risk.
- **inherent_risk** — surface inherent-risk columns alongside residual risk on assessments. _Default off._

## Compliance

- **compliance** — compliance assessments (audits). Effectively master switch for the entire compliance pillar.
- **auditee_mode** — the read-only auditee surface for external assessors. _Default off._
- **campaigns** — bulk-orchestration of audits across many perimeters. _PRO._

## Resilience

- **bia** — business impact analyses.

## Third-party and privacy

- **tprm** — third-party risk management.
- **contracts** — contracts surface inside TPRM. _Default off._
- **privacy** — the privacy register pillar (master switch).
- **personal_data** — personal-data inventory inside the privacy register.
- **purposes** — purposes register.
- **right_requests** — data-subject right requests.
- **data_breaches** — data-breach tracking.

## Catalog

- **security_advisories** — the security advisories catalogue.
- **cwes** — the CWE catalogue.

## Metrology and reporting

- **metrology** — metric definitions, instances, and dashboards.
- **reports** — the reports surface. _Default off._
- **advanced_analytics** — Per-audit [Advanced Analytics](../../features/audit-analytics.md) dashboard (compliance by section, controls coverage, timeline, evidence coverage, threats, exceptions). _Default off._

## Integrations and automation

- **outgoing_webhooks** — outgoing webhooks. _Default off._
- **chat_mode** — the in-product chat assistant. _Default off; only visible when `ENABLE_CHAT` is set on the instance._
- **terminologies** — organisation-specific label overrides.

## Project management

- **project_management** — projects, accreditations, responsibility matrices. _Default off._

## Workflow

- **journeys** — preset journeys for bootstrapping new organisations or domains.
- **comments** — comments on objects.
- **object_audit_trail** — per-object [audit trail](../../features/audit-log.md#per-object-audit-trail) button on detail pages, gated by the **Can view object audit trails** permission. _PRO._
- **focus_mode** — UI mode that filters the entire workspace to a single domain. _PRO. Default off._

## Experimental

- **experimental** — feature-gate for the experimental area. Use with caution.

> Defaults marked _Default off_ are off in fresh installs. Everything else defaults to on. Restart isn't required when a flag is toggled, but a hard refresh in the browser is.
