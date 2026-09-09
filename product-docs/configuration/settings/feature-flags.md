# Feature flags

Feature flags turn whole product areas on or off. They're how you tailor the navigation and the surface area to what your team actually uses, and how you keep experimental or specialised features out of sight until you want them.

Flags affect what's visible in the sidebar, what appears in CRUD pages, and which permissions are even relevant. They do **not** delete any underlying data — turning a flag off hides the feature; turning it back on restores the UI as it was.

## Operations

- **xrays** — the X-rays inconsistency-detection page.
- **incidents** — incident management.
- **tasks** — the task-management module (one-off and recurring tasks).
- **control_plan** — the consolidated control-plan view across applied controls.
- **workflows** — the [workflow builder](../../features/workflows/README.md): automation on a schedule, an event or a webhook. _Default off._

## Governance

- **risk_acceptances** — the risk-acceptance workflow.
- **exceptions** — security-exception tracking.
- **follow_up** — [findings binders](../../concepts/findings-assessments.md) and the standalone **Findings** list.
- **findings_from_requirements** — adds a **Findings** tab on a requirement assessment, so a finding can be raised straight from an audit. The audit's findings are collected in a binder created on first use. _Default off._
- **commitment_management** — [commitments](../../concepts/commitments.md): the delivery date an owner promises on an applied control or a one-off task, and its renegotiation. _Default off._
- **validation_flows** — configurable approval workflows that mirror internal review or management-approval processes, attached to objects whose state changes warrant sign-off. _Default off._
- **organisation_issues** — context register: issues affecting the organisation.
- **organisation_objectives** — context register: organisational objectives.
- **policy_documents** — the dedicated Policies surface (a filtered view of applied controls).
- **document_management** — the standalone [Documents](../../concepts/documents.md) module: the reading catalogue, document list, and templates. Author or upload documents through a draft → published lifecycle, independent of policies.

## Risk

- **ebiosrm** — the EBIOS RM module.
- **scoring_assistant** — the OWASP-based scoring assistant.
- **vulnerabilities** — vulnerability tracking.
- **quantitative_risk_studies** — Monte-Carlo quantitative risk.
- **inherent_risk** — surface inherent-risk columns alongside residual risk on assessments. _Default off._
- **threat_modeling** — the threat-modeling surface. _Default off._

## Compliance

- **compliance** — compliance assessments (audits). Effectively master switch for the entire compliance pillar.
- **auditee_mode** — the auditee surface external respondents land in.
- **campaigns** — [campaigns](../../features/campaigns.md): bulk-orchestration of assessments, either across your own perimeters or across a set of third parties. _PRO._
- **audit_tree_inheritance** — combine an audit's results with parent-domain audits on the same framework. Reveals the **Domain inheritance strategy** [general setting](general.md#domain-tree-audit-inheritance) and the **Combined view** on the [Framework report](../../features/framework-report.md#combined-view-domain-tree-inheritance). _Default off._
- **posture_assessments** — [technical postures](../../concepts/technical-postures.md): continuous measurement of assets against technical baselines (CIS Benchmarks, hardening guides) with recurring scan results. _Default off._

## Resilience

- **bia** — business impact analyses.

## Third-party and privacy

- **tprm** — third-party risk management.
- **contracts** — contracts surface inside TPRM. _Default off._
- **dora** — the DORA-specific fields on entities, solutions, assets and contracts, plus the [DORA reporting](../../features/framework-specific/dora.md) capabilities.
- **external_ratings** — [external ratings](../../concepts/third-party-risk.md#external-ratings): record scores published by rating services (SecurityScorecard, Bitsight, CyberVadis, …) against your third parties. _Default off._
- **privacy** — the privacy register pillar (master switch).
- **personal_data** — personal-data inventory inside the privacy register.
- **purposes** — purposes register.
- **right_requests** — data-subject right requests.
- **data_breaches** — data-breach tracking.

## Catalog

- **security_advisories** — the security advisories catalogue.
- **cwes** — the CWE catalogue.
- **ttps** — the TTP catalogues (MITRE ATT&CK, ATLAS): tactics and techniques. _Default off._

## Metrology and reporting

- **metrology** — metric definitions, instances, and dashboards.
- **reports** — the reports surface. _Default off._
- **advanced_analytics** — Per-audit [Advanced Analytics](../../features/audit-analytics.md) dashboard (compliance by section, controls coverage, timeline, evidence coverage, threats, exceptions).

## Integrations and automation

- **outgoing_webhooks** — outgoing webhooks. _Default off._
- **audit_log_forwarding** — [forward the audit log](../../integrations/audit-log-forwarding.md) to an external SIEM over HTTP or Kafka. _PRO. Default off._
- **jit_provisioning** — [SSO auto-provisioning](../sso/README.md#auto-provisioning-jit): auto-create an account on a user's first SSO login. Also unlocks the **IdP groups** menu and the **IdP groups** column on the users table (see `idp_groups` below), so auto-provisioned users can inherit roles through IdP group mapping.
- **idp_groups** — [SCIM 2.0 provisioning and IdP group mapping](../sso/scim.md): the SCIM settings tab, and — same as `jit_provisioning` above — the IdP groups menu and the IdP groups column on the users table. _PRO._
- **service_accounts** — [service accounts](../../integrations/service-accounts.md) for machine-to-machine API access via OAuth2 client credentials. _PRO._
- **chat_mode** — the in-product chat assistant. _Default off; only visible when `ENABLE_CHAT` is set on the instance._
- **infra_config_management** — the [allowed-IP whitelist](infra-config-allowed-ip.md) settings tab. _Only visible when `ENABLE_INFRA_CONFIG_MANAGEMENT` is set on the instance._
- **terminologies** — organisation-specific label overrides.
- **custom_fields** — org-defined typed fields on objects (Projects, Assets, Applied controls); see [Custom fields](../../features/custom-fields.md). _PRO. Default off._

## Project management

- **project_management** — projects, accreditations, responsibility matrices. _Default off._

## Workflow

- **journeys** — preset journeys for bootstrapping new organisations or domains.
- **comments** — comments on objects.
- **object_audit_trail** — per-object [audit trail](../../features/audit-log.md#per-object-audit-trail) button on detail pages, gated by the **Can view object audit trails** permission. _PRO._
- **focus_mode** — UI mode that filters the entire workspace to a single domain. _PRO. Default off._

## Publishing

- **custom_portals** — [portals and trust center](../../features/portals.md): the **Manage portals** admin surface and the public pages it publishes. _Default off._

## Experimental

- **experimental** — feature-gate for the experimental area. Use with caution.

> Defaults marked _Default off_ are off in fresh installs. Everything else defaults to on. Restart isn't required when a flag is toggled, but a hard refresh in the browser is.
